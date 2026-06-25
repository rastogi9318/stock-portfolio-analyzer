# AI Assistant Setup Guide

The portfolio analyzer now includes an AI Investment Advisor powered by **Groq** via the Groq OpenAI-compatible API.

## Setup Instructions

### Get an API Key

1. Visit [Groq Console](https://console.groq.com/docs/overview)
2. Sign up or log in to your account
3. Create a new API key
4. Copy the key

### Set Environment Variable

**On Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY = "your-api-key-here"
```

**On Windows (Command Prompt):**
```cmd
set GROQ_API_KEY=your-api-key-here
```

**On Mac/Linux:**
```bash
export GROQ_API_KEY="your-api-key-here"
```

### Verify Setup

- Run the app with `streamlit run app.py`
- After running analysis, you should see the AI advisor chat interface

### Persistent Setup (Optional)

To avoid setting environment variables every time, you can create a `.env` file:

1. In your project directory, create a file named `.env`:
   ```
   GROQ_API_KEY=your-api-key-here
   ```

2. Install python-dotenv:
   ```bash
   pip install python-dotenv
   ```

3. The app already loads environment variables from `.env` when `python-dotenv` is installed.

## Features

Once set up, after you run a portfolio analysis, you'll see the "AI Investment Advisor" section where you can:

- **Ask about specific stocks**: "Why did INFY get a BUY recommendation?"
- **Get portfolio insights**: "What's the risk profile of my portfolio?"
- **Understand metrics**: "What does ROE mean and why is it important?"
- **Get diversification advice**: "Should I add more tech stocks to my portfolio?"
- **Compare holdings**: "How does INFY compare to WIPRO?"
- **Get investment strategies**: "What's your take on my current allocations?"

## Notes

- **Groq is accessed through the Groq OpenAI-compatible API**
- **Privacy**: Your portfolio data is sent to the API provider for response generation
- **Rate Limits**: Refer to Groq documentation for limits
- **Token Limits**: Responses are capped at 1024 tokens for cost efficiency

## Troubleshooting

**"No AI provider available" message:**
- Verify `GROQ_API_KEY` is set correctly
- Restart Streamlit after setting environment variables

**Chat not responding:**
- Check your internet connection
- Verify the API key is valid
- Confirm your account has API access

**High costs:**
- Reduce chat frequency or use shorter questions
- Monitor your API usage in the Groq console
