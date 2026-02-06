# familybot/bot.py
import os
from datetime import datetime
from typing import Dict, List, Any

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from familybot import FamilyFinanceAgent, format_summary_ar


CHAT_NOTES: Dict[int, List[Dict[str, Any]]] = {}


def _get_members() -> List[str]:
    raw = os.getenv("FAMILY_MEMBERS", "")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts or ["Alex", "Jamie", "Sam"]


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "مرحباً 👋\nهذا بوت لمتابعة مصروف العائلة والقروض والأقساط.\nاكتب أي حركة مالية مثلاً:\n\"دفعت ٢٠٠ درهم بقالة للعائلة\"، ثم استخدم /summary لرؤية الملخص."
    await update.message.reply_text(text)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = []
    lines.append("الأوامر المتاحة:")
    lines.append("")
    lines.append("/start – بدء استخدام البوت")
    lines.append("/help – عرض هذه المساعدة")
    lines.append("/summary – ملخص حركات هذا الشهر")
    lines.append("/summary all – ملخص جميع الحركات المسجلة")
    lines.append("/loans – عرض القروض والأقساط الشهرية")
    lines.append("/reset – حذف جميع البيانات في هذه المحادثة")
    lines.append("")
    lines.append("أي رسالة عادية بدون أمر يتم اعتبارها حركة مالية.")
    lines.append("")
    lines.append("أمثلة:")
    lines.append("- دفعت ٢٠٠ درهم بقالة للعائلة")
    lines.append("- إيجار الشقة ٣٥٠٠ درهم دفعتها مريم")
    lines.append("- أحمد أخذ قرض سيارة ١٠٠٬٠٠٠ درهم ويسدد ٥٬٠٠٠ شهرياً")
    lines.append("- سلفة ٣٠٠ درهم من علي إلى خالد")
    lines.append("")
    lines.append("اكتب الحركات بشكل طبيعي، والبوت سيتولى التحليل.")
    await update.message.reply_text("\n".join(lines))


def _get_chat_notes(chat_id: int) -> List[Dict[str, Any]]:
    if chat_id not in CHAT_NOTES:
        CHAT_NOTES[chat_id] = []
    return CHAT_NOTES[chat_id]


async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    CHAT_NOTES.pop(chat_id, None)
    await update.message.reply_text("تم حذف جميع البيانات المسجلة لهذه المحادثة.")


async def note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    msg = update.message
    if msg is None or not msg.text:
        return
    notes = _get_chat_notes(chat_id)
    notes.append(
        {
            "text": msg.text,
            "created_at": datetime.utcnow().isoformat(),
        }
    )
    await msg.reply_text("تم تسجيل الحركة المالية.")


def _filter_notes_by_mode(
    notes: List[Dict[str, Any]], mode: str
) -> List[Dict[str, Any]]:
    if mode == "all":
        return notes
    now = datetime.utcnow()
    out: List[Dict[str, Any]] = []
    for n in notes:
        try:
            dt = datetime.fromisoformat(n["created_at"])
        except Exception:
            dt = now
        if dt.year == now.year and dt.month == now.month:
            out.append(n)
    return out


async def summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    notes = _get_chat_notes(chat_id)
    if not notes:
        await update.message.reply_text("لا توجد أي حركات مالية مسجلة بعد.")
        return
    mode = "month"
    if context.args:
        arg = context.args[0].strip().lower()
        if arg in {"all", "الكل"}:
            mode = "all"
    filtered = _filter_notes_by_mode(notes, mode)
    if not filtered:
        await update.message.reply_text("لا توجد حركات مالية في هذه الفترة.")
        return
    text_block = "\n".join(n["text"] for n in filtered)
    members = _get_members()
    agent = FamilyFinanceAgent(members)
    result = agent.analyze(text_block)
    if mode == "all":
        label = "ملخص جميع الحركات المسجلة:"
    else:
        label = "ملخص هذا الشهر:"
    summary_text = format_summary_ar(result, label)
    await update.message.reply_text(summary_text)


async def loans_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    notes = _get_chat_notes(chat_id)
    if not notes:
        await update.message.reply_text("لا توجد أي حركات مالية مسجلة بعد.")
        return
    text_block = "\n".join(n["text"] for n in notes)
    members = _get_members()
    agent = FamilyFinanceAgent(members)
    result = agent.analyze(text_block)
    loans = result.get("loans", [])
    if not loans:
        await update.message.reply_text("لا توجد قروض مسجلة حتى الآن.")
        return
    lines = ["القروض المسجلة:"]
    for loan in loans:
        borrower = loan["borrower"]
        principal = loan["principal"]
        monthly = loan["monthly_payment"]
        lines.append(
            f"- {borrower}: قرض قدره {principal:.2f} درهم، قسط شهري {monthly:.2f} درهم"
        )
    await update.message.reply_text("\n".join(lines))


def create_application() -> Application:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("reset", reset_handler))
    app.add_handler(CommandHandler("summary", summary_handler))
    app.add_handler(CommandHandler("loans", loans_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, note_handler)
    )
    return app


application: Application = create_application()


def main() -> None:
    application.run_polling()


if __name__ == "__main__":
    main()
