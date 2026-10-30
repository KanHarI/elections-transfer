"""Ballot letters → list names and display colors, per election.

Letters are reused across elections by unrelated lists (e.g. פה was Yesh Atid in
2022 and a minor list in 2026), so every mapping is election-specific.

Which lists get their own node is decided from the data (SMALL_PARTY_THRESHOLD);
these tables only supply labels. A list missing from a table falls back to its
letters.
"""

from dataclasses import dataclass

SMALL_PARTY_THRESHOLD = 0.002  # share of valid votes nationally, per election


@dataclass(frozen=True)
class Party:
    en: str
    he: str
    color: str = "#a0a4ab"


# 25th Knesset, 1 Nov 2022. Names from the CEC results / Hebrew Wikipedia.
K25: dict[str, Party] = {
    "מחל": Party("Likud", "הליכוד", "#1d4e9e"),
    "פה": Party("Yesh Atid", "יש עתיד", "#3fa9dc"),
    "ט": Party("Religious Zionism", "הציונות הדתית", "#b9741a"),
    "כן": Party("National Unity", "המחנה הממלכתי", "#5f7fc4"),
    "שס": Party("Shas", "ש״ס", "#3b3f6b"),
    "ג": Party("United Torah Judaism", "יהדות התורה", "#5b4a33"),
    "ל": Party("Yisrael Beiteinu", "ישראל ביתנו", "#7e3f98"),
    "עם": Party("Ra'am", "רע״ם", "#2e7d32"),
    "ום": Party("Hadash–Ta'al", "חד״ש–תע״ל", "#c62828"),
    "אמת": Party("Labor", "העבודה", "#e8615a"),
    "מרצ": Party("Meretz", "מרצ", "#5cb85c"),
    "ד": Party("Balad", "בל״ד", "#ad1457"),
    "ב": Party("Jewish Home", "הבית היהודי", "#93b84a"),
    "אצ": Party("Economic Freedom", "חופש כלכלי", "#b8a597"),
    "קץ": Party("Be'Ometz Bishvilcha", "באומץ בשבילך", "#9fb0ba"),
    "יז": Party("New Economic Party", "הכלכלית החדשה", "#8a9ba5"),
    "צ": Party("Tze'irim Bo'arim", "צעירים בוערים"),
    "ף": Party("Pirates", "הפיראטים"),
    "ק": Party("Kol HaSviva VeHaChai", "קול הסביבה והחי"),
    "ת": Party("Da'at Tov VaRa", "דעת טוב ורע"),
    "ני": Party("Netiv", "נתיב"),
    "קנ": Party("Kol Kol Kovea", "כל קול קובע"),
    "נק": Party("Yesh Kivun", "יש כיוון"),
    "י": Party("Free Democratic Israel", "ישראל חופשית דמוקרטית"),
    "קך": Party("Seder Hadash", "סדר חדש"),
    "נץ": Party("HaAtzmaim HaHadashim", "העצמאים החדשים"),
    "ץ": Party("Social Leadership", "מנהיגות חברתית"),
    "רז": Party("Shloshim/Arba'im", "רשימת שלושים/ארבעים"),
    "ך": Party("Ani VeAta", "אני ואתה"),
    "ז": Party("Shahar", "שחר כח חברתי"),
    "קי": Party("HaLev HaYehudi", "הלב היהודי"),
    "יק": Party("Biblical Bloc", "הגוש התנ״כי"),
    "נז": Party("Kvod HaAdam", "כבוד האדם"),
    "נר": Party("Anachnu", "אנחנו"),
    "זץ": Party("Tzomet", "צומת"),
    "יץ": Party("Tzav HaSha'a", "צו השעה"),
    "נף": Party("Shema", "שמע"),
    "ינ": Party("Ihud Bnei HaBrit", "איחוד בני הברית"),
    "זך": Party("Kama", "קמ״ה"),
    "זנ": Party("Koach Lehashpia", "כח להשפיע"),
}

# 26th Knesset, 27 Oct 2026. Names from the CEC list of submitted lists.
K26: dict[str, Party] = {
    "מחל": Party("Likud", "הליכוד", "#1d4e9e"),
    "דרך": Party("Yashar! (Eisenkot)", "ישר!", "#00897b"),
    "רק": Party("Beyachad (Bennett)", "ביחד", "#6a5acd"),
    "ודם": Party("Joint List", "הרשימה המשותפת", "#c62828"),
    "אמת": Party("The Democrats", "הדמוקרטים", "#e8615a"),
    "עם": Party("Ra'am", "רע״ם", "#2e7d32"),
    "ל": Party("Yisrael Beiteinu", "ישראל ביתנו", "#7e3f98"),
    "ב": Party("Otzma Yehudit", "עוצמה יהודית", "#e0a21b"),
    "ג": Party("United Torah Judaism", "יהדות התורה", "#5b4a33"),
    "שס": Party("Shas", "ש״ס", "#3b3f6b"),
    "ט": Party("Religious Zionism–Zehut", "הציונות הדתית וזהות", "#b9741a"),
    "די": Party("Reservists (Hendel–Zelekha)", "המילואימניקים והכלכלית", "#6f8a99"),
    "ך": Party("Amcha Yisrael (Winter)", "עמך ישראל", "#a1887f"),
    "נר": Party("Tzeva Shahor", "צבע שחור"),
    "זך": Party("HaTzibur HaHaredi", "הציבור החרדי"),
    "ני": Party("Noam", "נעם"),
    "בי": Party("Tzomet Beit Yisrael", "צומת בית ישראל"),
    "ד": Party("HaShutfut LaKulam", "השותפות לכולם"),
    "צדק": Party("Sharsheret", "שרשר לאהבה ואחדות העם"),
    "בד": Party("Beyachad Natzliach", "ביחד נצליח"),
    "רץ": Party("HaKahal", "הקהל"),
    "צף": Party("Pirates", "הפיראטים"),
    "י": Party("Israel First (Haskel)", "ישראל תחילה"),
    "נקי": Party("Electoral Reform", "התיקון לשיטת הבחירות והממשל"),
    "קך": Party("Seder Hadash", "סדר חדש"),
    "ה": Party("Gan Eden", "גן עדן"),
    "פה": Party("Ani VeAta", "אני ואתה"),
    "נף": Party("Shema", "שמע"),
    "קץ": Party("Mishpat Tzedek", "משפט צדק"),
    "בקר": Party("Orot HaShahar", "אורות השחר"),
    "קה": Party("Kol HaNashim", "קול הנשים"),
    "ק": Party("Tkuma", "תקומה"),
    "ז": Party("Betach", "בטח"),
    "נץ": Party("Bitachon Ishi", "ביטחון אישי"),
    "יק": Party("Biblical Bloc", "הגוש התנ״כי"),
    "זץ": Party("Brit Olam", "ברית עולם"),
    "צבי": Party("Tnuat Achai", "תנועת אחי"),
    "כן": Party("Blue and White", "כחול לבן"),
}

PARTIES = {25: K25, 26: K26}

# Non-party categories. NEW exists only on the 2022 side.
SPECIAL: dict[str, Party] = {
    "OTHER": Party("Other lists (<0.2%)", "רשימות אחרות", "#b9bec5"),
    "INVALID": Party("Invalid ballot", "קול פסול", "#cfd3d8"),
    "ABSTAIN": Party("Didn't vote", "לא הצביעו", "#8d939b"),
    "NEW": Party("New voters (net)", "בוחרים חדשים (נטו)", "#c7d6df"),
}


def label(knesset: int, category: str) -> Party:
    if category in SPECIAL:
        return SPECIAL[category]
    letters = category.removeprefix("P:")
    return PARTIES[knesset].get(letters, Party(letters, letters))
