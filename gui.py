import queue
import threading
import tkinter as tk
import types
from tkinter import ttk
from main import (
    buildLeaderboard, compareStatRows, currentSeason, efgper, findPlayerID,
    getSeasonRow, getTeamRow, getWeekStats,
    leaderboardStats, normalizeSeason, per36, percalc, threeparate, tsper,
    usgcalc, vorpcalc,
)

# =====================================================================
# SECTION 1: WINDOW SETUP
# =====================================================================
BG = "#F3F6FB"
CARD = "#FFFFFF"
NAVY = "#10243A"
NAVY_HOVER = "#1C3855"
ORANGE = "#F47B35"
ORANGE_HOVER = "#D96120"
TEXT = "#172B42"
MUTED = "#66778A"
BORDER = "#DCE4ED"
ERROR = "#A33A2B"
WHITE = "#FFFFFF"
INPUT_BG = "#F5F7FA"        # text field background
SURFACE_HOVER = "#E8EEF5"   # hover color for white buttons / menus
TABLE_HEADER = "#EEF2F7"
ROW_ALT = "#F7F9FC"         # every other leaderboard row
SELECTED = "#FCE6D9"        # selected leaderboard row
HEADER_KICKER = "#F6A46F"   # small orange text in the navy header
HEADER_SUBTLE = "#C2D0DE"   # subtitle text in the navy header
ACCENT_TEXT = "#C2541A"     # darker orange, readable as text on light backgrounds
FONT = "Segoe UI"


# =====================================================================
# SHARED WIDGET HELPERS - change these to restyle the whole app
# =====================================================================
def setHoverColors(widget, normal, hover):
    """Set a widget's resting and hover background colors."""
    widget.hoverColors = (normal, hover)
    widget.configure(bg = normal, activebackground = hover)


def addHover(widget, normal, hover):
    """Swap to the hover color while the mouse is over the widget."""
    setHoverColors(widget, normal, hover)

    def onEnter(_event):
        if str(widget["state"]) != "disabled":
            widget.configure(bg = widget.hoverColors[1])

    def onLeave(_event):
        widget.configure(bg = widget.hoverColors[0])

    widget.bind("<Enter>", onEnter)
    widget.bind("<Leave>", onLeave)


def makeEntry(parent, width = 32):
    return tk.Entry(parent, font = (FONT, 10), width = width, bd = 0,
                    bg = INPUT_BG, fg = TEXT, insertbackground = TEXT,
                    highlightthickness = 1, highlightbackground = BORDER,
                    highlightcolor = ORANGE)


def makeButton(parent, text, command, small = False):
    """Orange call-to-action button with a hover effect."""
    button = tk.Button(parent, text = text, command = command,
                       font = (FONT, 9 if small else 10, "bold"), fg = WHITE,
                       activeforeground = WHITE, bd = 0,
                       padx = 18 if small else 24, pady = 8 if small else 9,
                       cursor = "hand2", relief = "flat")
    addHover(button, ORANGE, ORANGE_HOVER)
    return button


def submitOnEnter(entries, button):
    """Pressing Enter in any of these fields clicks the button (ignored while it's disabled)."""
    for entry in entries:
        entry.bind("<Return>", lambda _event: button.invoke())


class ResultCard(tk.Frame):
    """Shows a result as a big number with a caption, or a short message.

    showResult() takes a dict:
        value    - the big number, e.g. "61.8%" (optional)
        label    - what the number is, e.g. "True shooting %"
        subtitle - e.g. "Stephen Curry · 2024-25" (optional)
        rows     - list of (name, value) pairs shown as a grid (optional)
    """

    def __init__(self, parent, placeholder = "Your result will appear here.", wraplength = 520,
                 reserveBadgeSpace = False):
        super().__init__(parent, bg = INPUT_BG, highlightthickness = 1,
                         highlightbackground = BORDER, highlightcolor = BORDER, padx = 18, pady = 12)
        self.placeholder = placeholder
        # side-by-side cards keep room for the badge so both stay the same height
        self.reserveBadgeSpace = reserveBadgeSpace
        self.badge = tk.Label(self, text = "▲ HIGHER", font = (FONT, 8, "bold"),
                              bg = ORANGE, fg = WHITE, padx = 6, pady = 1)
        self.value = tk.Label(self, font = (FONT, 24, "bold"), bg = INPUT_BG, fg = TEXT)
        self.caption = tk.Label(self, font = (FONT, 9, "bold"), bg = INPUT_BG, fg = MUTED)
        self.subtitle = tk.Label(self, font = (FONT, 9), bg = INPUT_BG, fg = MUTED)
        self.rows = tk.Frame(self, bg = INPUT_BG)
        self.message = tk.Label(self, font = (FONT, 10, "bold"), bg = INPUT_BG, fg = MUTED,
                                wraplength = wraplength, justify = "center")
        self.reset()

    def _clear(self):
        for widget in (self.badge, self.value, self.caption, self.subtitle, self.rows, self.message):
            widget.pack_forget()
        for widget in self.rows.winfo_children():
            widget.destroy()

    def reset(self):
        self.showMessage(self.placeholder)

    def showMessage(self, text, color = MUTED):
        self._clear()
        self.message.config(text = text, fg = color)
        self.message.pack(pady = 6)

    def showResult(self, result, highlight = False, rowHighlights = None):
        """highlight marks the whole value as the better one; rowHighlights does it per grid row."""
        self._clear()
        if highlight:
            self.badge.config(bg = ORANGE, fg = WHITE)
            self.badge.pack(pady = (0, 4))
        elif self.reserveBadgeSpace and "value" in result:
            self.badge.config(bg = INPUT_BG, fg = INPUT_BG)   # invisible placeholder
            self.badge.pack(pady = (0, 4))
        if "value" in result:
            self.value.config(text = result["value"], fg = ACCENT_TEXT if highlight else TEXT)
            self.value.pack()
        self.caption.config(text = result["label"].upper())
        self.caption.pack()
        if result.get("subtitle"):
            self.subtitle.config(text = result["subtitle"])
            self.subtitle.pack(pady = (2, 0))
        for index, (name, value) in enumerate(result.get("rows", [])):
            isBetter = bool(rowHighlights and rowHighlights[index])
            tk.Label(self.rows, text = name, font = (FONT, 10), bg = INPUT_BG, fg = MUTED,
                     anchor = "w").grid(row = index, column = 0, sticky = "w", padx = (0, 28))
            tk.Label(self.rows, text = value, font = (FONT, 10, "bold"), bg = INPUT_BG,
                     fg = ACCENT_TEXT if isBetter else TEXT,
                     anchor = "e").grid(row = index, column = 1, sticky = "e")
        if result.get("rows"):
            self.rows.pack(pady = (8, 0))

root = tk.Tk()

root.title("National Basketball Association Advanced Statistics Calculator")
root.geometry("920x820")
root.minsize(760, 680)
root.configure(bg = BG)


def runInBackground(work, onDone, onError):
    """Run work() on a worker thread so the window stays responsive.

    onDone(result) or onError(exception) is called back on the Tk thread.
    """
    resultQueue = queue.Queue()

    def worker():
        try:
            resultQueue.put((True, work()))
        except Exception as error:
            resultQueue.put((False, error))

    def poll():
        try:
            ok, value = resultQueue.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        (onDone if ok else onError)(value)

    threading.Thread(target = worker, daemon = True).start()
    root.after(100, poll)

header = tk.Frame(root, bg = NAVY, height = 112)
header.pack(fill = "x")
header.pack_propagate(False)

tk.Label(header, text = "COURTSIDE  /  NBA ADVANCED STATS", font = (FONT, 10, "bold"),
         bg = NAVY, fg = HEADER_KICKER).pack(anchor = "w", padx = 32, pady = (18, 3))
tk.Label(header, text = "Basketball Statistics Studio", font = (FONT, 23, "bold"),
         bg = NAVY, fg = WHITE).pack(anchor = "w", padx = 32)
tk.Label(header, text = "Calculate custom metrics or explore a player's season.",
         font = (FONT, 10), bg = NAVY, fg = HEADER_SUBTLE).pack(anchor = "w", padx = 34, pady = (2, 0))

navBar = tk.Frame(root, bg = BG, height = 58)
navBar.pack(fill = "x", padx = 24, pady = (10, 4))
navBar.pack_propagate(False)

contentArea = tk.Frame(root, bg = BG)
contentArea.pack(fill = "both", expand = True, padx = 24, pady = (0, 20))

# =====================================================================
# SECTION 2: THE THREE SCREENS (frames stacked in the same spot)
# =====================================================================
pageCalc = tk.Frame(contentArea, bg = BG)
pageStats = tk.Frame(contentArea, bg = BG)
pageCompare = tk.Frame(contentArea, bg = BG)
pageLeader = tk.Frame(contentArea, bg = BG)

for page in (pageCalc, pageStats, pageCompare, pageLeader):
    page.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)

leaderCard = tk.Frame(pageLeader, bg = CARD, highlightbackground = BORDER, highlightcolor = BORDER, highlightthickness = 1)
leaderCard.place(relx = 0.5, rely = 0.08, relwidth = 0.92, relheight = 0.88, anchor = "n")
tk.Label(leaderCard, text = "Weekly Player Leaders", font = (FONT, 19, "bold"),
         bg = CARD, fg = TEXT).pack(pady = (20, 3))
tk.Label(leaderCard, text = "Top performers from the last 7 days · minimum 2 games",
         font = (FONT, 10), bg = CARD, fg = MUTED).pack(pady = (0, 14))

leaderControls = tk.Frame(leaderCard, bg = CARD)
leaderControls.pack(fill = "x", padx = 24, pady = (0, 12))
tk.Label(leaderControls, text = "Rank by", font = (FONT, 9, "bold"),
         bg = CARD, fg = MUTED).pack(side = "left", padx = (0, 8))

leaderStatKeys = {info["label"]: key for key, info in leaderboardStats.items()}
selectedLeaderStat = tk.StringVar(value = leaderboardStats["1"]["label"])
leaderMenu = tk.OptionMenu(
    leaderControls, selectedLeaderStat, *leaderStatKeys.keys(),
    command = lambda _choice: loadLeaderboard(),
)
leaderMenu.pack(side = "left")

leaderRefreshButton = makeButton(leaderControls, "Refresh", lambda: loadLeaderboard(), small = True)
leaderRefreshButton.pack(side = "right")

leaderStatus = tk.Label(leaderCard, text = "Choose a statistic and refresh to load this week's leaders.",
                        font = (FONT, 9), bg = CARD, fg = MUTED, anchor = "w", wraplength = 680)
leaderStatus.pack(fill = "x", padx = 24, pady = (0, 8))

leaderTableFrame = tk.Frame(leaderCard, bg = CARD)
leaderTableFrame.pack(fill = "both", expand = True, padx = 24, pady = (0, 22))

leaderStyle = ttk.Style(root)
leaderStyle.configure(
    "Leader.Treeview", font = (FONT, 10), rowheight = 31,
    background = CARD, fieldbackground = CARD, foreground = TEXT,
)
leaderStyle.configure(
    "Leader.Treeview.Heading", font = (FONT, 9, "bold"),
    background = TABLE_HEADER, foreground = TEXT, relief = "flat",
)
leaderStyle.map("Leader.Treeview", background=[("selected", SELECTED)],
                foreground=[("selected", TEXT)])

leaderColumns = ("rank", "player", "team", "value")
leaderTable = ttk.Treeview(
    leaderTableFrame, columns = leaderColumns, show = "headings",
    style = "Leader.Treeview", height = 10,
)
for column, heading, width, anchor in (
    ("rank", "RANK", 72, "center"),
    ("player", "PLAYER", 310, "w"),
    ("team", "TEAM", 110, "center"),
    ("value", "VALUE", 150, "center"),
):
    leaderTable.heading(column, text = heading)
    leaderTable.column(column, width = width, anchor = anchor, stretch = column == "player")
leaderTable.tag_configure("stripe", background = ROW_ALT)

leaderScrollbar = ttk.Scrollbar(leaderTableFrame, orient = "vertical", command = leaderTable.yview)
leaderTable.configure(yscrollcommand = leaderScrollbar.set)
leaderTable.pack(side = "left", fill = "both", expand = True)
leaderScrollbar.pack(side = "right", fill = "y")

leaderLoadInProgress = False

# =====================================================================
# SECTION 3: SCREEN SWITCHING AND THE TOP BUTTONS
# =====================================================================
def showPage(page):
    page.tkraise()
    for navPage, button in navButtons.items():
        isActive = navPage == page
        if isActive:
            setHoverColors(button, ORANGE, ORANGE_HOVER)
        else:
            setHoverColors(button, CARD, SURFACE_HOVER)
        button.configure(
            fg = WHITE if isActive else TEXT,
            activeforeground = WHITE if isActive else TEXT,
            relief = "flat",
        )
    if page == pageLeader:
        loadLeaderboard()


def loadLeaderboard():
    global leaderLoadInProgress
    if leaderLoadInProgress:
        return

    statKey = leaderStatKeys[selectedLeaderStat.get()]
    leaderLoadInProgress = True
    leaderRefreshButton.configure(state = "disabled")
    leaderMenu.configure(state = "disabled")
    leaderStatus.configure(text = f"Loading {leaderboardStats[statKey]['label']} leaders…", fg = MUTED)
    for item in leaderTable.get_children():
        leaderTable.delete(item)

    def fetchResults():
        df = getWeekStats()
        if df.empty:
            return [], "No games found in the last 7 days."
        info = leaderboardStats[statKey]
        results = buildLeaderboard(df, info["calc"], 2, info["minFga"])[:10]
        message = None if results else "No players qualified for this leaderboard in the last 7 days."
        return results, message

    def finishLoading():
        global leaderLoadInProgress
        leaderLoadInProgress = False
        leaderRefreshButton.configure(state = "normal")
        leaderMenu.configure(state = "normal")

    def onDone(outcome):
        finishLoading()
        results, message = outcome
        if message:
            leaderStatus.configure(text = message, fg = MUTED)
            return
        info = leaderboardStats[statKey]
        leaderStatus.configure(text = f"Top 10 · {info['label']} · last 7 days", fg = MUTED)
        for rank, (name, team, value) in enumerate(results, start = 1):
            shownValue = f"{value:.1%}" if info["percent"] else f"{value:.1f}"
            tags = ("stripe",) if rank % 2 == 0 else ()
            leaderTable.insert("", "end", values = (rank, name, team, shownValue), tags = tags)

    def onError(error):
        finishLoading()
        leaderStatus.configure(
            text = f"Could not load leaderboard. Check your connection and try again. ({error})",
            fg = ERROR,
        )

    runInBackground(fetchResults, onDone, onError)

navButtons = {}
for page, label in ((pageCalc, "Calculator"), (pageStats, "Statistics"),
                    (pageCompare, "Compare"), (pageLeader, "Leaderboard")):
    button = tk.Button(
        navBar, text = label, command = lambda selectedPage = page: showPage(selectedPage),
        font = (FONT, 10, "bold"), bd = 0, padx = 20, pady = 9, cursor = "hand2",
        fg = TEXT, activeforeground = TEXT,
        relief = "flat", highlightthickness = 1, highlightbackground = BORDER,
    )
    addHover(button, CARD, SURFACE_HOVER)
    button.pack(side = "left", padx = (0, 9), pady = 7)
    navButtons[page] = button

buttonCalc = navButtons[pageCalc]
buttonStats = navButtons[pageStats]
buttonCompare = navButtons[pageCompare]
buttonLeader = navButtons[pageLeader]

# =====================================================================
# SECTION 4: CALCULATOR SCREEN - form-building helper
# =====================================================================
def showOutcome(card, outcome):
    """Lookups return a dict for a result, or a plain string when something is wrong."""
    if isinstance(outcome, str):
        card.showMessage(outcome, ERROR)
    else:
        card.showResult(outcome)


def makeCalcForm(parent, title, fields, calculate):
    frame = tk.Frame(parent, bg = CARD, highlightbackground = BORDER, highlightcolor = BORDER, highlightthickness = 1)
    frame.place(relx = 0.5, rely = 0.14, relwidth = 0.86, relheight = 0.83, anchor = "n")
    tk.Label(frame, text = title, font = (FONT, 17, "bold"),
             bg = CARD, fg = TEXT).pack(pady = (18, 12))

    # long forms (USG% has 8 fields) go in two columns so they don't run off the card
    columns = 2 if len(fields) > 4 else 1
    fieldsFrame = tk.Frame(frame, bg = CARD)
    fieldsFrame.pack()
    entries = []
    for index, labelText in enumerate(fields):
        cell = tk.Frame(fieldsFrame, bg = CARD)
        cell.grid(row = index // columns, column = index % columns, padx = 10, pady = (0, 4))
        tk.Label(cell, text = labelText, font = (FONT, 9, "bold"),
                 bg = CARD, fg = MUTED).pack(pady = (3, 2))
        entry = makeEntry(cell, width = 32 if columns == 1 else 24)
        entry.pack()
        entries.append(entry)

    resultCard = ResultCard(frame)

    def onClick():
        try:
            values = [float(e.get()) for e in entries]
        except ValueError:
            resultCard.showMessage("Please enter numbers only.", ERROR)
            return
        showOutcome(resultCard, calculate(*values))

    calcButton = makeButton(frame, "Calculate", onClick)
    calcButton.pack(pady = 14)
    submitOnEnter(entries, calcButton)
    resultCard.pack(fill = "x", padx = 48, pady = (0, 14))
    return frame

# =====================================================================
# SECTION 5: CALCULATOR SCREEN - one small function per stat
# =====================================================================
def calcTS(points, fga, fta):
    return {"value": f"{tsper(points, fga, fta):.1%}", "label": "True shooting %"}

def calcEFG(fgm, tpm, fga):
    return {"value": f"{efgper(fgm, tpm, fga):.1%}", "label": "Effective field goal %"}

def calcVORP(boxPm, minPlay, teamGames):
    if teamGames == 0:
        return "Team games can't be 0."
    minPer = minPlay / (48 * teamGames)
    return {"value": f"{vorpcalc(boxPm, minPer, teamGames):.1f}", "label": "Value over replacement player"}

def calcUSG(fga, fta, tov, mp, tmFga, tmFta, tmMp, tmTov):
    usg = usgcalc(fga, fta, tov, mp, tmFga, tmFta, tmTov, tmMp)
    return {"value": f"{usg:.1f}", "label": "Usage rate"}

# =====================================================================
# SECTION 6: STATISTICS SCREEN - Form Building
# =====================================================================
def makeStatsForm(parent, title, fields, lookup):
    frame = tk.Frame(parent, bg = CARD, highlightbackground = BORDER, highlightcolor = BORDER, highlightthickness = 1)
    frame.place(relx = 0.5, rely = 0.14, relwidth = 0.86, relheight = 0.83, anchor = "n")
    tk.Label(frame, text = title, font = (FONT, 17, "bold"),
             bg = CARD, fg = TEXT).pack(pady = (22, 16))

    entries = []
    for labelText in fields:
        tk.Label(frame, text = labelText, font = (FONT, 9, "bold"),
                 bg = CARD, fg = MUTED).pack(pady = (6, 3))
        entry = makeEntry(frame, width = 34)
        if labelText == "Season":
            entry.insert(0, currentSeason())
        entry.pack()
        entries.append(entry)

    resultCard = ResultCard(frame)

    def onDone(outcome):
        lookupButton.configure(state = "normal")
        showOutcome(resultCard, outcome)

    def onError(error):
        lookupButton.configure(state = "normal")
        if isinstance(error, ValueError):
            message = "Please enter a valid number for Box +/-."
        else:
            message = "Statistics lookup failed. Check your connection and inputs."
        resultCard.showMessage(message, ERROR)

    def onClick():
        values = [entry.get().strip() for entry in entries]
        if any(not value for value in values):
            resultCard.showMessage("Please fill in every field.", ERROR)
            return
        lookupButton.configure(state = "disabled")
        resultCard.showMessage("Looking up statistics…")
        runInBackground(lambda: lookup(*values), onDone, onError)

    lookupButton = makeButton(frame, "Look up statistics", onClick)
    lookupButton.pack(pady = 16)
    submitOnEnter(entries, lookupButton)
    resultCard.pack(fill = "x", padx = 48, pady = (0, 14))
    return frame


def getStatsRow(name, season):
    playerID = findPlayerID(name)
    if playerID is None:
        return None, "Player not found. Check the player's full name."
    normalizedSeason = normalizeSeason(season)
    row = getSeasonRow(playerID, normalizedSeason)
    if row is None:
        return None, "No stats found for that player and season."
    return row, None


def playerSubtitle(name, season):
    return f"{name} · {normalizeSeason(season)}"


PER36_STATS = [("Points", "PTS"), ("Rebounds", "REB"), ("Assists", "AST"),
               ("Blocks", "BLK"), ("Steals", "STL"), ("Turnovers", "TOV")]


def lookupTS(name, season):
    row, error = getStatsRow(name, season)
    if error:
        return error
    return {"value": f"{tsper(row['PTS'], row['FGA'], row['FTA']):.1%}",
            "label": "True shooting %", "subtitle": playerSubtitle(name, season)}


def lookupEFG(name, season):
    row, error = getStatsRow(name, season)
    if error:
        return error
    return {"value": f"{efgper(row['FGM'], row['FG3M'], row['FGA']):.1%}",
            "label": "Effective field goal %", "subtitle": playerSubtitle(name, season)}


def lookupVORP(name, season, boxPm):
    row, error = getStatsRow(name, season)
    if error:
        return error
    if row['TEAM_ID'] == 0:
        return "Team stats are unavailable for players traded midseason."
    team = getTeamRow(row['TEAM_ID'], season)
    teamGames = team['GP']
    if teamGames == 0:
        return "The player's team has not played any games this season."
    minPer = row['MIN'] / (48 * teamGames)
    return {"value": f"{vorpcalc(float(boxPm), minPer, teamGames):.1f}",
            "label": "Value over replacement player", "subtitle": playerSubtitle(name, season)}


def lookupUSG(name, season):
    row, error = getStatsRow(name, season)
    if error:
        return error
    if row['TEAM_ID'] == 0:
        return "Team stats are unavailable for players traded midseason."
    team = getTeamRow(row['TEAM_ID'], season)
    teamMp = team['MIN'] * 5
    value = usgcalc(
        row['FGA'], row['FTA'], row['TOV'], row['MIN'],
        team['FGA'], team['FTA'], team['TOV'], teamMp,
    )
    return {"value": f"{value:.1f}", "label": "Usage rate", "subtitle": playerSubtitle(name, season)}


def lookupPer36(name, season):
    row, error = getStatsRow(name, season)
    if error:
        return error
    rows = [(label, f"{per36(row[column], row['MIN']):.1f}") for label, column in PER36_STATS]
    return {"label": "Per 36 minutes", "subtitle": playerSubtitle(name, season), "rows": rows}


def lookupThreePointRate(name, season):
    row, error = getStatsRow(name, season)
    if error:
        return error
    value = threeparate(row['FG3A'], row['FGA'])
    return {"value": f"{value:.3f}", "label": "3-point attempt rate",
            "subtitle": playerSubtitle(name, season)}


def lookupPER(name, season):
    row, error = getStatsRow(name, season)
    if error:
        return error
    value = percalc(
        row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK'],
        row['FGA'] - row['FGM'], row['FTA'] - row['FTM'], row['TOV'], row['GP'],
    )
    return {"value": f"{value:.3f}", "label": "Player efficiency rating",
            "subtitle": playerSubtitle(name, season)}


# =====================================================================
# SECTION 7: CALCULATOR AND STATISTICS SCREEN FORMS
# =====================================================================
forms = {
    "True Shooting % (TS%)": makeCalcForm(pageCalc, "True Shooting % (TS%)",
        ["Points", "Field goal attempts", "Free throw attempts"], calcTS),
    "Effective FG% (eFG%)": makeCalcForm(pageCalc, "Effective FG% (eFG%)",
        ["Field goals made", "3-pointers made", "Field goal attempts"], calcEFG),
    "VORP": makeCalcForm(pageCalc, "Value Over Replacement Player (VORP)",
        ["Box +/-", "Total minutes played", "Team games played"], calcVORP),
    "Usage Rate (USG%)": makeCalcForm(pageCalc, "Usage Rate (USG%)",
        ["Field goals attempted", "Free throws attempted", "Turnovers", "Minutes played",
         "Team FGA", "Team FTA", "Team minutes", "Team turnovers"], calcUSG),
}

selectedCalc = tk.StringVar(value = "True Shooting % (TS%)")

def styleOptionMenu(widget):
    widget.configure(
        font = (FONT, 10, "bold"), fg = TEXT, activeforeground = TEXT,
        bd = 0, padx = 12, pady = 7, cursor = "hand2",
        highlightthickness = 1, highlightbackground = BORDER, relief = "flat",
    )
    addHover(widget, CARD, SURFACE_HOVER)
    widget["menu"].configure(
        font = (FONT, 10), bg = CARD, fg = TEXT,
        activebackground = SURFACE_HOVER, activeforeground = TEXT,
        bd = 0, relief = "flat",
    )

def onPickCalc(name):
    forms[name].tkraise()

menuCalc = tk.OptionMenu(pageCalc, selectedCalc, *forms.keys(), command = onPickCalc)
menuCalc.place(relx = 0.5, rely = 0.05, anchor = "center")
styleOptionMenu(menuCalc)

onPickCalc(selectedCalc.get())

statsForms = {
    "True Shooting % (TS%)": makeStatsForm(pageStats, "True Shooting % (TS%)",
        ["Player name", "Season"], lookupTS),
    "Effective FG% (eFG%)": makeStatsForm(pageStats, "Effective FG% (eFG%)",
        ["Player name", "Season"], lookupEFG),
    "VORP": makeStatsForm(pageStats, "Value Over Replacement Player (VORP)",
        ["Player name", "Season", "Box +/-"], lookupVORP),
    "Usage Rate (USG%)": makeStatsForm(pageStats, "Usage Rate (USG%)",
        ["Player name", "Season"], lookupUSG),
    "Per 36 Minutes": makeStatsForm(pageStats, "Player Stats Per 36 Minutes",
        ["Player name", "Season"], lookupPer36),
    "Three Point Attempt Rate": makeStatsForm(pageStats, "Three Point Attempt Rate",
        ["Player name", "Season"], lookupThreePointRate),
    "Player Efficiency Rating (PER)": makeStatsForm(pageStats, "Player Efficiency Rating (PER)",
        ["Player name", "Season"], lookupPER),
}

selectedStats = tk.StringVar(value = "True Shooting % (TS%)")

def onPickStats(name):
    statsForms[name].tkraise()

menuStats = tk.OptionMenu(pageStats, selectedStats, *statsForms.keys(), command = onPickStats)
menuStats.place(relx = 0.5, rely = 0.05, anchor = "center")
styleOptionMenu(menuStats)

onPickStats(selectedStats.get())

# =====================================================================
# SECTION 8: COMPARE SCREEN - two players side by side
# =====================================================================
comparisonStatKeys = {
    "True Shooting % (TS%)": "1",
    "Effective FG% (eFG%)": "2",
    "VORP": "3",
    "Usage Rate (USG%)": "4",
    "Per 36 Minutes": "5",
}

# how each single-number stat is labelled and shown; digits = display precision,
# so "better" is decided on the rounded number the user actually sees
COMPARE_DISPLAY = {
    "1": ("True shooting %", lambda v: f"{v:.1%}", 3),
    "2": ("Effective field goal %", lambda v: f"{v:.1%}", 3),
    "3": ("Value over replacement player", lambda v: f"{v:.1f}", 1),
    "4": ("Usage rate", lambda v: f"{v:.1f}", 1),
}
LOWER_IS_BETTER = {"Turnovers"}

selectedCompareStat = tk.StringVar(value = "True Shooting % (TS%)")

comparisonFrame = tk.Frame(pageCompare, bg = CARD, highlightbackground = BORDER, highlightcolor = BORDER, highlightthickness = 1)
comparisonFrame.place(relx = 0.5, rely = 0.08, relwidth = 0.92, relheight = 0.89, anchor = "n")

tk.Label(comparisonFrame, text = "Player Comparison", font = (FONT, 18, "bold"),
         bg = CARD, fg = TEXT).pack(pady = (20, 10))

compareControls = tk.Frame(comparisonFrame, bg = CARD)
compareControls.pack(pady = (0, 6))
comparisonMenu = tk.OptionMenu(compareControls, selectedCompareStat, *comparisonStatKeys.keys())
comparisonMenu.pack(side = "left", padx = (0, 10))
styleOptionMenu(comparisonMenu)

comparisonStatus = tk.Label(
    comparisonFrame, text = "Pick a statistic, enter two players, then press Compare.",
    font = (FONT, 9), bg = CARD, fg = MUTED, wraplength = 680,
)
comparisonStatus.pack(pady = (4, 12))

compareSides = tk.Frame(comparisonFrame, bg = CARD)
compareSides.pack(fill = "x", padx = 28)
compareSides.grid_columnconfigure(0, weight = 1, uniform = "side")
compareSides.grid_columnconfigure(2, weight = 1, uniform = "side")
tk.Label(compareSides, text = "VS", font = (FONT, 13, "bold"),
         bg = CARD, fg = MUTED).grid(row = 0, column = 1, sticky = "n", padx = 16, pady = (58, 0))


def makeCompareSide(column, heading):
    side = tk.Frame(compareSides, bg = CARD)
    side.grid(row = 0, column = column, sticky = "nsew")
    side.grid_columnconfigure(0, weight = 1, uniform = "field")
    side.grid_columnconfigure(1, weight = 1, uniform = "field")

    def fieldLabel(text, row, col, colspan = 1):
        label = tk.Label(side, text = text, font = (FONT, 9, "bold"), bg = CARD, fg = MUTED)
        label.grid(row = row, column = col, columnspan = colspan, sticky = "w", pady = (6, 2),
                   padx = (0, 8) if col == 0 else (8, 0))
        return label

    tk.Label(side, text = heading.upper(), font = (FONT, 10, "bold"), bg = CARD,
             fg = TEXT).grid(row = 0, column = 0, columnspan = 2, sticky = "w")
    fieldLabel("Player name", 1, 0, colspan = 2)
    nameEntry = makeEntry(side, width = 10)
    nameEntry.grid(row = 2, column = 0, columnspan = 2, sticky = "ew", ipady = 3)
    fieldLabel("Season", 3, 0)
    seasonEntry = makeEntry(side, width = 10)
    seasonEntry.grid(row = 4, column = 0, sticky = "ew", padx = (0, 8), ipady = 3)
    seasonEntry.insert(0, currentSeason())
    boxPmLabel = fieldLabel("Box +/-", 3, 1)
    boxPmEntry = makeEntry(side, width = 10)
    boxPmEntry.grid(row = 4, column = 1, sticky = "ew", padx = (8, 0), ipady = 3)

    card = ResultCard(side, placeholder = "—", wraplength = 260, reserveBadgeSpace = True)
    card.grid(row = 5, column = 0, columnspan = 2, sticky = "ew", pady = (14, 0))

    return types.SimpleNamespace(name = nameEntry, season = seasonEntry, boxPm = boxPmEntry,
                                 boxPmLabel = boxPmLabel, card = card)


compareLeft = makeCompareSide(0, "Player 1")
compareRight = makeCompareSide(2, "Player 2")


def updateCompareFields():
    for side in (compareLeft, compareRight):
        if selectedCompareStat.get() == "VORP":
            side.boxPmLabel.grid()
            side.boxPm.grid()
        else:
            side.boxPmLabel.grid_remove()
            side.boxPm.grid_remove()
        side.card.reset()


def isBetter(mine, theirs, digits, lowerIsBetter = False):
    mine, theirs = round(mine, digits), round(theirs, digits)
    return mine < theirs if lowerIsBetter else mine > theirs


def showComparison(statKey, name1, season1, name2, season2, left, right):
    sides = ((compareLeft, name1, season1, left, right), (compareRight, name2, season2, right, left))
    if statKey == "5":
        for side, name, season, mine, theirs in sides:
            rows, highlights = [], []
            for (label, _column), myValue, theirValue in zip(PER36_STATS, mine, theirs):
                rows.append((label, f"{myValue:.1f}"))
                highlights.append(isBetter(myValue, theirValue, 1, label in LOWER_IS_BETTER))
            side.card.showResult({"label": "Per 36 minutes", "subtitle": f"{name} · {season}",
                                  "rows": rows}, rowHighlights = highlights)
        comparisonStatus.config(text = "The better value in each row is highlighted (fewer turnovers is better).",
                                fg = MUTED)
        return

    label, formatValue, digits = COMPARE_DISPLAY[statKey]
    for side, name, season, mine, theirs in sides:
        side.card.showResult({"value": formatValue(mine), "label": label,
                              "subtitle": f"{name} · {season}"},
                             highlight = isBetter(mine, theirs, digits))
    if round(left, digits) == round(right, digits):
        comparisonStatus.config(text = "These players are tied on this statistic.", fg = MUTED)
    else:
        comparisonStatus.config(text = "The higher value is highlighted.", fg = MUTED)


def onComparePlayers():
    statKey = comparisonStatKeys[selectedCompareStat.get()]
    name1 = compareLeft.name.get().strip()
    season1 = normalizeSeason(compareLeft.season.get().strip() or currentSeason())
    name2 = compareRight.name.get().strip()
    season2 = normalizeSeason(compareRight.season.get().strip() or currentSeason())
    needsTeams = statKey in ("3", "4")

    def fail(message):
        comparisonStatus.config(text = message, fg = ERROR)
        compareLeft.card.reset()
        compareRight.card.reset()

    if not name1 or not name2:
        fail("Please enter both player names.")
        return

    # validate Box +/- up front so bad input never triggers a network call
    boxPm1Value = boxPm2Value = None
    if statKey == "3":
        if not compareLeft.boxPm.get().strip() or not compareRight.boxPm.get().strip():
            fail("Please enter Box +/- values for both players to compare VORP.")
            return
        try:
            boxPm1Value = float(compareLeft.boxPm.get())
            boxPm2Value = float(compareRight.boxPm.get())
        except ValueError:
            fail("Box +/- values must be numbers.")
            return

    def work():
        row1, error1 = getStatsRow(name1, season1)
        if error1:
            return {"error": f"Player 1: {error1}"}
        row2, error2 = getStatsRow(name2, season2)
        if error2:
            return {"error": f"Player 2: {error2}"}

        team1 = team2 = None
        if needsTeams:
            if row1["TEAM_ID"] == 0 or row2["TEAM_ID"] == 0:
                return {"error": "Team stats are unavailable for players traded midseason."}
            team1 = getTeamRow(row1["TEAM_ID"], season1)
            team2 = getTeamRow(row2["TEAM_ID"], season2)
            if team1["GP"] == 0 or team2["GP"] == 0:
                return {"error": "One of these teams has not played any games yet."}

        left, right = compareStatRows(statKey, row1, row2, team1, team2, boxPm1Value, boxPm2Value)
        return {"left": left, "right": right}

    def onDone(outcome):
        compareButton.configure(state = "normal")
        if "error" in outcome:
            fail(outcome["error"])
            return
        showComparison(statKey, name1, season1, name2, season2, outcome["left"], outcome["right"])

    def onError(error):
        compareButton.configure(state = "normal")
        if isinstance(error, ValueError):
            fail(str(error))
        else:
            fail("The comparison could not be completed. Check your connection, player names and seasons.")

    compareButton.configure(state = "disabled")
    comparisonStatus.config(text = "Comparing players…", fg = MUTED)
    compareLeft.card.showMessage("Loading…")
    compareRight.card.showMessage("Loading…")
    runInBackground(work, onDone, onError)


compareButton = makeButton(compareControls, "Compare players", onComparePlayers)
compareButton.pack(side = "left")
submitOnEnter([compareLeft.name, compareLeft.season, compareLeft.boxPm,
               compareRight.name, compareRight.season, compareRight.boxPm], compareButton)

selectedCompareStat.trace_add("write", lambda *_: updateCompareFields())
updateCompareFields()

# bomboclat wallahi....
showPage(pageCalc)

root.mainloop()
