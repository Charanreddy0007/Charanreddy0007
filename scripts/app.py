import json
import base64
import mimetypes
import urllib.request
import urllib.parse
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path
from html import escape


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = BASE_DIR / "data" / "leetcodeResponse.json"
OUTPUT_FILE = BASE_DIR / "assets" / "stats.svg"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

WIDTH = 1600
HEIGHT = 670

# Difficulty bar coordinates
BAR_X1 = 578
BAR_X2 = 1453
BAR_WIDTH = BAR_X2 - BAR_X1


# ============================================================
# LOAD JSON
# ============================================================

with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)


# ============================================================
# DATA
# ============================================================

# ============================================================
# EXTRACT LEETCODE DATA
# ============================================================

# Your JSON structure is:
#
# data
#   └── data
#       └── matchedUser
#
# ============================================================

leetcode_data = data.get("data", {})

user = leetcode_data.get("matchedUser", {})


# ============================================================
# PROFILE
# ============================================================

username = user.get(
    "username",
    ""
)

user_profile = user.get(
    "profile",
    {}
)

profile_url = (
    f"https://leetcode.com/u/{username}/"
)

avatar_source = user_profile.get(
    "userAvatar",
    ""
)

rank = user_profile.get(
    "ranking",
    0
)


# ============================================================
# SUBMISSION DATA
# ============================================================

submit_stats = user.get(
    "submitStats",
    {}
)

total_submissions = submit_stats.get(
    "totalSubmissionNum",
    []
)

accepted_submissions = submit_stats.get(
    "acSubmissionNum",
    []
)


# ============================================================
# HELPER
# ============================================================

def get_difficulty_count(items, difficulty_name):
    """
    Find the solved/submission count for a difficulty.
    """

    for item in items:

        if item.get("difficulty") == difficulty_name:

            return item.get("count", 0)

    return 0


def get_difficulty_submissions(items, difficulty_name):
    """
    Find total submission attempts for a difficulty.
    """

    for item in items:

        if item.get("difficulty") == difficulty_name:

            return item.get("submissions", 0)

    return 0


# ============================================================
# SOLVED COUNTS
# ============================================================

solved = get_difficulty_count(
    accepted_submissions,
    "All"
)

easy = get_difficulty_count(
    accepted_submissions,
    "Easy"
)

medium = get_difficulty_count(
    accepted_submissions,
    "Medium"
)

hard = get_difficulty_count(
    accepted_submissions,
    "Hard"
)


# ============================================================
# ACCEPTANCE RATE
# ============================================================

total_attempts = get_difficulty_submissions(
    total_submissions,
    "All"
)

accepted_attempts = get_difficulty_submissions(
    accepted_submissions,
    "All"
)


if total_attempts > 0:

    acceptance = (
        accepted_attempts
        / total_attempts
        * 100
    )

else:

    acceptance = 0


# ============================================================
# STREAK
# ============================================================

calendar = user.get(
    "userCalendar",
    {}
)

streak = calendar.get(
    "streak",
    0
)


# ============================================================
# DIFFICULTY PERCENTAGES
# ============================================================
#
# The SVG wants percentages.
#
# Your JSON gives:
#
# Easy   = 62 solved
# Medium = 18 solved
# Hard   = 1 solved
#
# Total = 81
#
# Therefore:
#
# Easy   = 62 / 81 * 100
# Medium = 18 / 81 * 100
# Hard   = 1 / 81 * 100
#
# ============================================================

if solved > 0:

    easy = (
        easy
        / solved
        * 100
    )

    medium = (
        medium
        / solved
        * 100
    )

    hard = (
        hard
        / solved
        * 100
    )

else:

    easy = 0
    medium = 0
    hard = 0


# ============================================================
# BADGES
# ============================================================

badges = user.get(
    "badges",
    []
)



# ============================================================
# FORMAT NUMBERS
# ============================================================

def format_number(value):
    """
    Format numbers nicely.

    Example:
        81 -> 81
        1968960 -> 1,968,960
    """

    if isinstance(value, float):
        if value.is_integer():
            value = int(value)

    if isinstance(value, int):
        return f"{value:,}"

    return str(value)


def format_percentage(value):
    """
    Format percentage.

    Example:
        69.2 -> 69.2
        69 -> 69
    """

    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value)}%"

        return f"{value:.1f}%"

    return f"{value}%"


rank_display = format_number(rank)

solved_display = format_number(solved)

streak_display = f"{format_number(streak)} days"

acceptance_display = format_percentage(acceptance)

easy_display = format_percentage(easy)

medium_display = format_percentage(medium)

hard_display = format_percentage(hard)



# ============================================================
# IMAGE HELPERS
# ============================================================

def is_url(value):
    """
    Check whether a value is a URL.
    """

    if not value:
        return False

    parsed = urllib.parse.urlparse(value)

    return parsed.scheme in (
        "http",
        "https"
    )


def download_url(url, retries=2):
    """
    Download a remote file.
    If a relative URL fails, retry using https://leetcode.com/
    """

    urls_to_try = [url]

    # If URL is a relative LeetCode path,
    # try adding https://leetcode.com/
    if url.startswith("/"):
        urls_to_try.append(
            "https://leetcode.com" + url
        )

    for current_url in urls_to_try:

        request = urllib.request.Request(
            current_url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        for attempt in range(1, retries + 1):
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=60
                ) as response:
                    return response.read()

            except Exception as e:
                print(
                    f"WARNING: Image failed "
                    f"(attempt {attempt}/{retries}): "
                    f"{current_url} -> {e}"
                )

        print(
            f"Image failed: {current_url}"
        )

    return None

def get_file_bytes(source):
    """
    Read either a local file or remote URL.

    If a path starts with '/',
    first try it as a local project path.
    If it does not exist, try https://leetcode.com + path.
    """

    if not source:
        return None

    # Normal full URL
    if is_url(source):
        return download_url(source)

    # ---------------------------------------------------------
    # Relative/absolute-looking LeetCode path
    # Example:
    # /static/images/badges/guardian.png
    # ---------------------------------------------------------

    if source.startswith("/"):
        local_path = Path(__file__).parent / source.lstrip("/")

        if local_path.exists():
            return local_path.read_bytes()

        # Local file doesn't exist.
        # Try LeetCode website.
        fallback_url = "https://leetcode.com" + source

        return download_url(fallback_url)

    # ---------------------------------------------------------
    # Normal local relative file
    # ---------------------------------------------------------

    path = Path(source)

    if not path.exists():
        path = Path(__file__).parent / source

    if not path.exists():
        print(
            f"WARNING: File not found: {source}"
        )
        return None

    return path.read_bytes()


def get_mime_type(source):
    """
    Determine MIME type.
    """

    if is_url(source):
        path = urllib.parse.urlparse(
            source
        ).path

        mime = mimetypes.guess_type(
            path
        )[0]

    else:
        mime = mimetypes.guess_type(
            source
        )[0]

    return mime or "application/octet-stream"


def image_to_data_uri(source):
    """
    Convert an image to a base64 data URI.

    This prevents GitHub from having to load
    external image URLs from inside the SVG.
    """

    if not source:
        return ""

    try:

        raw = get_file_bytes(source)

        if raw is None:
            return ""

        mime = get_mime_type(source)

        encoded = base64.b64encode(
            raw
        ).decode("ascii")

        return (
            f"data:{mime};base64,{encoded}"
        )

    except Exception as e:

        print(
            f"WARNING: Could not embed image "
            f"{source}: {e}"
        )

        return ""



# ============================================================
# BADGES — 4 × 2
# ============================================================

badge_svg = []


BADGE_START_X = 67
BADGE_START_Y = 410

BADGE_SIZE = 70

BADGE_GAP_X = 9
BADGE_GAP_Y = 12


for index, badge in enumerate(badges[:8]):

    # LeetCode badge image
    image_source = badge.get(
        "icon",
        ""
    )

    # Clicking a badge opens the user's LeetCode profile
    badge_url = profile_url


    # --------------------------------------------------------
    # Position
    # --------------------------------------------------------

    column = index % 4
    row = index // 4


    x = (
        BADGE_START_X
        + column
        * (BADGE_SIZE + BADGE_GAP_X)
    )

    y = (
        BADGE_START_Y
        + row
        * (BADGE_SIZE + BADGE_GAP_Y)
    )


    # --------------------------------------------------------
    # Embed badge image
    # --------------------------------------------------------

    image_data = image_to_data_uri(
        image_source
    )


    if not image_data:

        print(
            f"WARNING: Could not load badge: "
            f"{image_source}"
        )

        continue


    badge_svg.append(
        f"""
        <a href="{escape(str(badge_url))}"
           target="_blank">

            <rect
                x="{x}"
                y="{y}"
                width="{BADGE_SIZE}"
                height="{BADGE_SIZE}"
                rx="12"
                fill="#191d21"
                stroke="#343a40"/>

            <image
                href="{image_data}"
                x="{x + 10}"
                y="{y + 10}"
                width="50"
                height="50"
                preserveAspectRatio="xMidYMid meet"/>

        </a>
        """
    )


badges_svg = "\n".join(
    badge_svg
)

badge_count = len(badges)


# ============================================================
# HEATMAP
# ============================================================

def parse_submission_calendar(value):
    """Parse LeetCode's submissionCalendar JSON string safely."""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return {int(k): int(v) for k, v in parsed.items()}
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
    if isinstance(value, dict):
        try:
            return {int(k): int(v) for k, v in value.items()}
        except (TypeError, ValueError):
            return {}
    return {}


submission_calendar = parse_submission_calendar(
    user.get("submissionCalendar", {})
)


def build_heatmap_svg(calendar_data, width=1035, height=125):
    """Create an inline contribution heatmap from submissionCalendar."""
    if not calendar_data:
        return ""

    dates = {
        datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).date(): count
        for ts, count in calendar_data.items()
    }

    if not dates:
        return ""

    # Show the latest 53 weeks, aligned Sunday -> Saturday.
    end_date = max(dates)
    end_sunday = end_date - datetime.timedelta(days=(end_date.weekday() + 1) % 7)
    start_sunday = end_sunday - datetime.timedelta(weeks=52)

    cols = 53
    rows = 7
    gap = 3
    cell = min(
        (width - (cols - 1) * gap) / cols,
        (height - (rows - 1) * gap) / rows,
    )

    max_count = max(dates.values()) or 1

    def level(count):
        if count <= 0:
            return 0
        ratio = count / max_count
        if ratio <= 0.25:
            return 1
        if ratio <= 0.50:
            return 2
        if ratio <= 0.75:
            return 3
        return 4

    fills = {
        0: "#252a2f",
        1: "#173f35",
        2: "#176b50",
        3: "#16a674",
        4: "#20c997",
    }

    cells = []

    for col in range(cols):
        for row in range(rows):
            current = start_sunday + datetime.timedelta(
                weeks=col,
                days=row,
            )
            count = dates.get(current, 0)
            x = col * (cell + gap)
            y = row * (cell + gap)

            cells.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" '
                f'width="{cell:.1f}" height="{cell:.1f}" '
                f'rx="2" fill="{fills[level(count)]}">'
                f'<title>{escape(current.isoformat())}: {count} submissions</title>'
                f'</rect>'
            )

    return "\n".join(cells)


heatmap_content = build_heatmap_svg(submission_calendar)

if heatmap_content:
    heatmap_svg = f"""
    <g id="contribution-heatmap"
       transform="translate(515 470)">
      {heatmap_content}
    </g>
    """
else:
    heatmap_svg = """
    <text
        x="995"
        y="535"
        text-anchor="middle"
        fill="#6b7280"
        font-family="monospace"
        font-size="13">
        Heatmap unavailable
    </text>
    """

# ============================================================
# AVATAR
# ============================================================

avatar_data = image_to_data_uri(avatar_source)

if not avatar_data:
    # Transparent 1x1 fallback
    avatar_data = (
        "data:image/gif;base64,"
        "R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="
    )


# ============================================================
# MAIN SVG
# ============================================================

svg = f"""<?xml version="1.0" encoding="UTF-8"?>

<svg xmlns="http://www.w3.org/2000/svg"
     width="1600"
     height="670"
     viewBox="0 0 1600 670">

  <defs>

    <!-- =====================================================
         MATTE CARD BACKGROUND
         ===================================================== -->

    <linearGradient id="cardBg"
                    x1="0"
                    y1="0"
                    x2="1"
                    y2="1">

      <stop offset="0%" stop-color="#151a20"/>
      <stop offset="50%" stop-color="#101419"/>
      <stop offset="100%" stop-color="#17131f"/>

    </linearGradient>


    <!-- subtle top-left blue -->
    <radialGradient id="blueGlow"
                     cx="0"
                     cy="0"
                     r="1">

      <stop offset="0%" stop-color="#284f86" stop-opacity=".32"/>
      <stop offset="100%" stop-color="#284f86" stop-opacity="0"/>

    </radialGradient>


    <!-- subtle purple bottom-right -->
    <radialGradient id="purpleGlow"
                     cx="1"
                     cy="1"
                     r="1">

      <stop offset="0%" stop-color="#7141a8" stop-opacity=".22"/>
      <stop offset="100%" stop-color="#7141a8" stop-opacity="0"/>

    </radialGradient>


    <!-- avatar purple -->
    <linearGradient id="avatarPurple"
                    x1="0"
                    y1="0"
                    x2="1"
                    y2="1">

      <stop offset="0%" stop-color="#b394ff"/>
      <stop offset="100%" stop-color="#8059e9"/>

    </linearGradient>


    <!-- easy -->
    <linearGradient
        id="easyGradient"
        gradientUnits="userSpaceOnUse"
        x1="578"
        y1="269"
        x2="1453"
        y2="269">

        <stop offset="0%" stop-color="#10b981"/>
        <stop offset="100%" stop-color="#19c99b"/>

    </linearGradient>


    <!-- medium -->
    <linearGradient
        id="mediumGradient"
        gradientUnits="userSpaceOnUse"
        x1="578"
        y1="307"
        x2="1453"
        y2="307">

        <stop offset="0%" stop-color="#3b82f6"/>
        <stop offset="100%" stop-color="#5595ff"/>

    </linearGradient>

    <!-- avatar crop -->
    <clipPath id="avatarClip">
      <circle cx="220"
              cy="128"
              r="51"/>
    </clipPath>


    <!-- subtle grid -->
    <pattern id="grid"
             width="50"
             height="50"
             patternUnits="userSpaceOnUse">

      <path d="M50 0H0V50"
            fill="none"
            stroke="#ffffff"
            stroke-opacity=".018"/>

    </pattern>

  </defs>



  <!-- =====================================================
       MAIN MATTE CARD

       The area outside this rectangle is TRANSPARENT.
       ===================================================== -->

  <rect x="20"
        y="20"
        width="1560"
        height="630"
        rx="30"
        fill="url(#cardBg)"
        stroke="#30363d"
        stroke-width="1"/>


  <!-- subtle background effects -->

  <rect x="20"
        y="20"
        width="1560"
        height="630"
        rx="30"
        fill="url(#grid)"/>

  <rect x="20"
        y="20"
        width="750"
        height="500"
        rx="30"
        fill="url(#blueGlow)"/>

  <rect x="850"
        y="200"
        width="730"
        height="450"
        rx="30"
        fill="url(#purpleGlow)"/>



  <!-- =====================================================
       LEFT PROFILE PANEL
       ===================================================== -->

  <rect x="45"
        y="45"
        width="370"
        height="580"
        rx="22"
        fill="#111417"
        fill-opacity=".92"
        stroke="#30363d"/>



  <!-- =====================================================
       AVATAR

       CHANGE:

       href="https://github.com/YOUR_USERNAME.png"

       href on <a> is the clickable profile URL.
       ===================================================== -->

  <a href="{escape(profile_url)}"
     target="_blank">

    <circle cx="220"
            cy="128"
            r="58"
            fill="url(#avatarPurple)"/>

    <image
      href="{avatar_data}"
      x="169"
      y="77"
      width="102"
      height="102"
      preserveAspectRatio="xMidYMid slice"
      clip-path="url(#avatarClip)"/>

  </a>


  <!-- =====================================================
       RANK
       ===================================================== -->

  <text x="165"
        y="215"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="13">
    Rank:
  </text>

  <!-- CHANGE THIS VALUE -->

  <text id="rank-value"
        x="210"
        y="215"
        fill="#9565ff"
        font-family="monospace"
        font-size="14"
        font-weight="700">
    {rank_display}
  </text>



  <line x1="67"
        y1="246"
        x2="393"
        y2="246"
        stroke="#30363d"/>



  <!-- =====================================================
       MAX STREAK
       ===================================================== -->

  <text x="67"
        y="278"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="14">
    Max Streak
  </text>

  <!-- CHANGE THIS -->

  <text id="streak-detail"
        x="393"
        y="278"
        text-anchor="end"
        fill="#12c996"
        font-family="monospace"
        font-size="14"
        font-weight="700">
    {streak_display}
  </text>



  <line x1="67"
        y1="301"
        x2="393"
        y2="301"
        stroke="#30363d"/>



  <!-- =====================================================
       ACCEPTANCE RATE
       ===================================================== -->

  <text x="67"
        y="334"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="14">
    Acceptance Rate
  </text>

  <!-- CHANGE THIS -->

  <text id="accept-detail"
        x="393"
        y="334"
        text-anchor="end"
        fill="#4c8dff"
        font-family="monospace"
        font-size="14"
        font-weight="700">
    {acceptance_display}
  </text>



  <line x1="67"
        y1="357"
        x2="393"
        y2="357"
        stroke="#30363d"/>



  <!-- =====================================================
       BADGES TITLE
       ===================================================== -->

  <text x="67"
        y="389"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="11"
        letter-spacing="3">
    BADGES
  </text>


  <!-- CHANGE THIS -->

  <text id="badges-value"
        x="393"
        y="389"
        text-anchor="end"
        fill="#9565ff"
        font-family="monospace"
        font-size="13">
    {badge_count}
  </text>



  <!-- =====================================================
       BADGES — 4 × 2

       Replace BADGE_IMAGE_xx with your SVG/image.

       Replace BADGE_URL_xx with the link.

       ===================================================== -->


<!-- =====================================================
     BADGES — 4 × 2
     ===================================================== -->


  {badges_svg}

  <!-- =====================================================
       SOLVED CARD
       ===================================================== -->

  <rect x="443"
        y="45"
        width="356"
        height="120"
        rx="20"
        fill="#15181b"
        stroke="#30363d"/>


  <!-- CHANGE THIS -->

  <text id="solved-value"
        x="621"
        y="105"
        text-anchor="middle"
        fill="#f1f3f5"
        font-family="Arial, sans-serif"
        font-size="36"
        font-weight="700">
    {solved_display}
  </text>


  <text x="621"
        y="135"
        text-anchor="middle"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="13"
        letter-spacing="1">
    SOLVED
  </text>



  <!-- =====================================================
       STREAK CARD
       ===================================================== -->

  <rect x="815"
        y="45"
        width="356"
        height="120"
        rx="20"
        fill="#15181b"
        stroke="#30363d"/>


  <!-- CHANGE THIS -->

  <text id="streak-value"
        x="993"
        y="105"
        text-anchor="middle"
        fill="#f1f3f5"
        font-family="Arial, sans-serif"
        font-size="36"
        font-weight="700">
    {format_number(streak)}
  </text>


  <text x="993"
        y="135"
        text-anchor="middle"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="13"
        letter-spacing="1">
    MAX STREAK (DAYS)
  </text>



  <!-- =====================================================
       ACCEPTANCE CARD
       ===================================================== -->

  <rect x="1187"
        y="45"
        width="356"
        height="120"
        rx="20"
        fill="#15181b"
        stroke="#30363d"/>


  <!-- CHANGE THIS -->

  <text id="accept-value"
        x="1365"
        y="105"
        text-anchor="middle"
        fill="#f1f3f5"
        font-family="Arial, sans-serif"
        font-size="36"
        font-weight="700">
    {int(acceptance)}
  </text>


  <text x="1365"
        y="135"
        text-anchor="middle"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="13"
        letter-spacing="1">
    ACCEPT %
  </text>



  <!-- =====================================================
       DIFFICULTY BREAKDOWN
       ===================================================== -->

  <rect x="443"
        y="190"
        width="1100"
        height="200"
        rx="20"
        fill="#15181b"
        stroke="#30363d"/>


  <!-- title -->

  <circle cx="479"
          cy="229"
          r="4"
          fill="#10c995"/>


  <text x="493"
        y="233"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="13"
        letter-spacing="3">
    DIFFICULTY BREAKDOWN
  </text>



  <!-- labels -->

  <text x="475"
        y="275"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="15">
    Easy
  </text>


  <text x="475"
        y="313"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="15">
    Medium
  </text>


  <text x="475"
        y="351"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="15">
    Hard
  </text>



  <!-- =====================================================
       EASY BAR

       pathLength="100" means:

       62 100 = 62%

       Change 62 to whatever percentage you provide.
       ===================================================== -->

  <line x1="578"
        y1="269"
        x2="1453"
        y2="269"
        stroke="#252a2f"
        stroke-width="9"
        stroke-linecap="round"/>


  <!-- CHANGE PERCENTAGE -->

  <line id="easy-bar"
        x1="578"
        y1="269"
        x2="1453"
        y2="269"
        pathLength="100"
        stroke="url(#easyGradient)"
        stroke-width="9"
        stroke-linecap="round"
        stroke-dasharray="{easy:.2f} 100"/>



  <!-- =====================================================
       MEDIUM BAR

       Change 18 to your percentage.
       ===================================================== -->

  <line x1="578"
        y1="307"
        x2="1453"
        y2="307"
        stroke="#252a2f"
        stroke-width="9"
        stroke-linecap="round"/>


  <line id="medium-bar"
        x1="578"
        y1="307"
        x2="1453"
        y2="307"
        pathLength="100"
        stroke="url(#mediumGradient)"
        stroke-width="9"
        stroke-linecap="round"
        stroke-dasharray="{medium:.2f} 100"/>



  <!-- =====================================================
       HARD BAR

       Change 1 to your percentage.
       ===================================================== -->

  <line x1="578"
        y1="345"
        x2="1453"
        y2="345"
        stroke="#252a2f"
        stroke-width="9"
        stroke-linecap="round"/>


  <line id="hard-bar"
        x1="578"
        y1="345"
        x2="1453"
        y2="345"
        pathLength="100"
        stroke="#925bef"
        stroke-width="9"
        stroke-linecap="round"
        stroke-dasharray="{hard:.2f} 100"/>



  <!-- percentage values -->

  <text id="easy-value"
        x="1510"
        y="275"
        text-anchor="end"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="14">
    {easy_display}
  </text>


  <text id="medium-value"
        x="1510"
        y="313"
        text-anchor="end"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="14">
    {medium_display}
  </text>


  <text id="hard-value"
        x="1510"
        y="351"
        text-anchor="end"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="14">
    {hard_display}
  </text>



  <!-- =====================================================
       CONTRIBUTION HEATMAP
       ===================================================== -->

  <rect x="443"
        y="410"
        width="1100"
        height="215"
        rx="20"
        fill="#15181b"
        stroke="#30363d"/>


  <circle cx="479"
          cy="448"
          r="4"
          fill="#10c995"/>


  <text x="493"
        y="452"
        fill="#a8b0bb"
        font-family="monospace"
        font-size="13"
        letter-spacing="3">
    CONTRIBUTION HEATMAP
  </text>



  <!-- =====================================================
       HEATMAP CONTENT

       Put your heatmap SVG in the same repository:

           heatmap.svg

       Then this works:

           href="heatmap.svg"

       Or:

           href="./heatmap.svg"

       ===================================================== -->

  {heatmap_svg}



</svg>
"""


# ============================================================
# WRITE SVG
# ============================================================

Path(OUTPUT_FILE).write_text(
    svg,
    encoding="utf-8"
)


# ============================================================
# DONE
# ============================================================

print()
print("=" * 60)
print("SVG GENERATED SUCCESSFULLY")
print("=" * 60)
print()
print(f"Input : {DATA_FILE}")
print(f"Output: {OUTPUT_FILE}")
print()
print("Statistics:")
print(f"  Rank       : {rank_display}")
print(f"  Solved     : {solved_display}")
print(f"  Streak     : {streak_display}")
print(f"  Acceptance : {acceptance_display}")
print()
print("Difficulty:")
print(f"  Easy       : {easy_display}")
print(f"  Medium     : {medium_display}")
print(f"  Hard       : {hard_display}")
print()
print(f"Badges      : {badge_count}")
print("Heatmap     : inline submissionCalendar")
print()


print(image_source)