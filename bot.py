"""
EEE Routine Bot (Simple + PDF-parsing)
- Uses PyPDF2 to extract text from the uploaded PDF routine.
- On /start asks user Level-Term (e.g., 1-1, 2-1, ...).
- /today and /tomorrow show only entries for that Level-Term (theory + lab).

Requirements:
pip install pyTelegramBotAPI PyPDF2
(If using Replit, add those to requirements.)
Place the routine PDF in the same folder and set PDF_PATH correctly.
"""

import telebot
import datetime
import re
from PyPDF2 import PdfReader

# ---------- CONFIG ----------
BOT_TOKEN = "8380820208:AAGOGG7QxuFNdr_rosTN38_7dGK1Qb81_xQ"
PDF_PATH = "EEE_routine.pdf"   # <-- put the uploaded PDF filename here
DAYS = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
# valid level-terms:
VALID_LT = {"1-1","1-2","2-1","2-2","3-1","3-2","4-1","4-2"}
# ----------------------------

bot = telebot.TeleBot(BOT_TOKEN)
user_levelterm = {}   # in-memory: { user_id: "2-1" }

# ---------- PDF helper ----------
def extract_pdf_text(path):
    """Extract raw text from all pages of the PDF (returns single string)."""
    try:
        reader = PdfReader(path)
        pages = []
        for p in reader.pages:
            txt = p.extract_text()
            if txt:
                pages.append(txt)
        return "\n".join(pages)
    except Exception as e:
        print("PDF read error:", e)
        return ""

def split_into_day_blocks(full_text):
    """
    Return dict day -> block_text.
    Heuristic: Find lines like 'Theory Saturday', 'Theory Sunday', ... and slice blocks.
    """
    blocks = {}
    # Normalize spacing, keep newlines
    text = full_text
    # Build pattern positions
    positions = []
    for day in DAYS:
        # look for "Theory <Day>" or "<Day> Routine" as anchors (case-insensitive)
        m = re.search(rf"(Theory\s+{day})|(Class Routine\s+{day})|(\b{day}\b)", text, flags=re.IGNORECASE)
        if m:
            positions.append((m.start(), day))
    # if anchors not all found, fallback: try matching day name anywhere (first occurrence)
    # Sort positions by index
    positions.sort()
    if not positions:
        # fallback whole text as 'All'
        blocks["ALL"] = text
        return blocks
    # build slices
    for i, (pos, day) in enumerate(positions):
        start = pos
        end = positions[i+1][0] if i+1 < len(positions) else len(text)
        block = text[start:end].strip()
        blocks[day] = block
    return blocks

def find_entries_for_levelterm(block_text, levelterm):
    """
    From a day's block, return lines that contain the given level-term.
    We'll pick lines that mention the pattern '2-1' or '2-1 ' or '2-1\t' or '2-1)' etc.
    Also try to include neighboring lines (context) when a match found (for lab/theory separation).
    """
    if not block_text:
        return []

    lines = block_text.splitlines()
    results = []
    pattern = re.compile(rf"\b{re.escape(levelterm)}\b", flags=re.IGNORECASE)
    for i, line in enumerate(lines):
        if pattern.search(line):
            # add the line; also try to grab previous/next short lines if they look like time/room parts
            context = [line.strip()]
            # previous line (if short and contains time or room indicators)
            if i-1 >= 0:
                prev = lines[i-1].strip()
                if prev and (re.search(r"\d{1,2}:\d{2}", prev) or len(prev) < 100):
                    context.insert(0, prev)
            if i+1 < len(lines):
                nxt = lines[i+1].strip()
                if nxt and (re.search(r"\d{1,2}:\d{2}", nxt) or len(nxt) < 120):
                    context.append(nxt)
            results.append(" | ".join([c for c in context if c]))
    # de-duplicate and return
    seen = []
    for r in results:
        if r not in seen:
            seen.append(r)
    return seen

def build_reply_for_day(full_text, day, levelterm):
    """
    Build a friendly message for a day & levelterm.
    """
    blocks = split_into_day_blocks(full_text)
    # prefer exact day block
    block = blocks.get(day) or blocks.get(day.capitalize()) or blocks.get("ALL") or ""
    matches = find_entries_for_levelterm(block, levelterm)
    if not matches:
        return f"No classes found for *{levelterm}* on *{day}*. 🎉"
    reply = f"📅 *{day}* — Routine for *{levelterm}*\n\n"
    # we'll try to separate 'Lab' vs 'Theory' by simple keywords, but if unknown show entries
    theory_lines = []
    lab_lines = []
    for m in matches:
        # heuristics: if the line contains 'Lab' or 'Physics Lab' or 'AB-2' etc -> lab
        if re.search(r"\b(Lab|Lab\W|Physics Lab|Chemistry Lab|AB-2|Lab:)\b", m, flags=re.IGNORECASE) or re.search(r"\bLab\b", m, flags=re.IGNORECASE):
            lab_lines.append(m)
        else:
            theory_lines.append(m)
    if theory_lines:
        reply += "📘 *Theory / Lectures:*\n"
        for l in theory_lines:
            reply += f"- {l}\n"
        reply += "\n"
    if lab_lines:
        reply += "🧪 *Lab / Practical:*\n"
        for l in lab_lines:
            reply += f"- {l}\n"
    # fallback if nothing categorized
    if not theory_lines and not lab_lines:
        for l in matches:
            reply += f"- {l}\n"
    return reply

# ---------- Bot handlers ----------
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    user_id = msg.from_user.id
    bot.reply_to(msg, "👋 Welcome to DIU EEE Routine Bot!\nPlease enter your Level–Term (e.g., 1-1, 2-1, 3-2):")
    bot.register_next_step_handler(msg, handle_levelterm)

def handle_levelterm(msg):
    user_id = msg.from_user.id
    lt = msg.text.strip()
    if lt not in VALID_LT:
        bot.reply_to(msg, "Invalid input. Please reply like `2-1` or `3-2` (no extra text). Try /start again.")
        return
    user_levelterm[user_id] = lt
    bot.reply_to(msg, f"✅ Saved Level–Term: *{lt}*.\nNow use /today or /tomorrow to see your classes.", parse_mode="Markdown")

@bot.message_handler(commands=['today'])
def cmd_today(msg):
    user_id = msg.from_user.id
    if user_id not in user_levelterm:
        bot.reply_to(msg, "Please set your Level–Term first using /start.")
        return
    lt = user_levelterm[user_id]
    day = datetime.datetime.now().strftime("%A")
    full_text = extract_pdf_text(PDF_PATH)
    if not full_text:
        bot.reply_to(msg, "Sorry, I couldn't read the routine PDF. Make sure the file exists on the server and PDF_PATH is correct.")
        return
    reply = build_reply_for_day(full_text, day, lt)
    bot.reply_to(msg, reply, parse_mode="Markdown")

@bot.message_handler(commands=['tomorrow'])
def cmd_tomorrow(msg):
    user_id = msg.from_user.id
    if user_id not in user_levelterm:
        bot.reply_to(msg, "Please set your Level–Term first using /start.")
        return
    lt = user_levelterm[user_id]
    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%A")
    full_text = extract_pdf_text(PDF_PATH)
    if not full_text:
        bot.reply_to(msg, "Sorry, I couldn't read the routine PDF. Make sure the file exists on the server and PDF_PATH is correct.")
        return
    reply = build_reply_for_day(full_text, tomorrow, lt)
    bot.reply_to(msg, reply, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def cmd_help(msg):
    bot.reply_to(msg, "Commands:\n/start — register your Level–Term\n/today — show today's classes for your Level–Term\n/tomorrow — show tomorrow's classes\n\nIf the bot fails to find classes, check that your Level–Term (e.g., 2-1) matches how the PDF lists Level-Terms.")

# ---------- start ----------
if __name__ == "__main__":
    print("Starting EEE Routine Bot (PDF-parsing) ...")
    bot.infinity_polling()
