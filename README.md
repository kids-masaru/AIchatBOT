# Mora - AI Secretary for LINE

Python-based AI secretary that integrates with LINE.
Powered by Gemini 3.0 Flash.

## Features

- **Conversation**: Natural chat with context awareness.
- **Google Workspace**:
    - **Gmail**: Check unread emails, summarize threads.
    - **Drive**: Search files, **read PDF content**.
    - **Docs/Sheets/Slides**: Create new documents.
    - **Calendar**: Check and add events.
- **Web**: Google Search, URL content fetching.
- **Tools**: Calculator, Date calculation, Weather/Outfit forecast.

## Deployment

This project is designed to be deployed on Vercel (recommended) or Railway.

## Local Development

```bash
pip install -r requirements.txt
functions-framework --target=webhook --port=8080
```
