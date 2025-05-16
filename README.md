# Bezstreem 🤖

Bezstreem is a Telegram automation bot designed to simplify and streamline daily operations on the Kerala BEVCO portal. It helps generate invoices, stock reports, and inventory downloads efficiently with a simple chat interface. Ideal for authorized users who manage retail or distribution tasks.

## Features 🚀

- 📄 Generate invoices with custom date input
- 📦 Download stock and inventory reports
- 🤖 Automated login with CAPTCHA handling
- 📁 Zips and delivers reports directly in chat
- 🔒 Restricted to authorized Telegram users

## Setup 🛠️

1. **Clone the repo**
   ```bash
   git clone https://github.com/your-username/Bezstreem.git
   cd Bezstreem
   ```

2. **Create and update `.env`**
   ```env
   BOT_TOKEN=your_telegram_bot_token
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## Notes 📌

- Make sure to update the list of `AUTHORIZED_USERS` inside the script with your Telegram ID.
- Don't forget to add `__pycache__/`, `.env`, and `*.xlsx` to `.gitignore`.

## License

This project is for internal use and not intended for public deployment.

---

> Developed with ❤️ by Pradip Paul 