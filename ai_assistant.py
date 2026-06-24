"""AI Chat Assistant for Portfolio Analysis Insights."""

import os
import pandas as pd
import requests
import streamlit as st
from datetime import datetime

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_llm_provider():
    """Detect if Groq is available via GROQ_API_KEY."""
    return "groq" if os.getenv("GROQ_API_KEY") else None


def build_portfolio_context(results: pd.DataFrame, df: pd.DataFrame) -> str:
    """Build a comprehensive context string from portfolio analysis results."""
    
    total_invested = df["buy_value"].sum() if "buy_value" in df.columns else 0
    total_current = results["closing_value"].sum() if "closing_value" in results.columns else 0
    total_pnl = results["unrealized_pnl"].sum() if "unrealized_pnl" in results.columns else 0
    avg_score = results["score"].dropna().mean()
    
    rec_counts = results["recommendation"].value_counts().to_dict() if "recommendation" in results.columns else {}
    
    context = f"""
# Portfolio Analysis Context

## Portfolio Summary
- Total Invested Value: ₹{total_invested:,.0f}
- Current Portfolio Value: ₹{total_current:,.0f}
- Unrealized P&L: ₹{total_pnl:,.0f}
- Average Stock Score: {avg_score:.2f}/10
- Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Recommendation Distribution
- BUY: {rec_counts.get('BUY', 0)} stocks
- HOLD: {rec_counts.get('HOLD', 0)} stocks
- SELL: {rec_counts.get('SELL', 0)} stocks
- N/A: {rec_counts.get('N/A', 0)} stocks

## Holdings Details
"""
    
    if "nse_symbol" in results.columns:
        for _, row in results.iterrows():
            symbol = row.get("nse_symbol", "N/A")
            recommendation = row.get("recommendation", "N/A")
            score = row.get("score", "N/A")
            explanation = row.get("explanation", "No explanation available")
            
            context += f"\n### {symbol}\n"
            context += f"- Recommendation: {recommendation}\n"
            context += f"- Score: {score}\n"
            context += f"- Analysis: {explanation}\n"
    
    return context


def chat_with_groq(messages: list, system_prompt: str) -> str:
    """Chat with Groq via the Groq OpenAI-compatible API."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "No Groq API key found. Set GROQ_API_KEY."

    url = "https://api.groq.com/openai/v1/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "openai/gpt-oss-20b",
        "input": [
            {"role": "system", "content": system_prompt},
            *messages,
        ],
        "temperature": 0.7,
        "max_output_tokens": 1024,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("output_text"):
            return data["output_text"].strip()

        # Groq OpenAI-compatible responses may return top-level output list
        if isinstance(data.get("output"), list):
            parts = []
            for item in data["output"]:
                if isinstance(item, dict):
                    if isinstance(item.get("content"), list):
                        for content_item in item["content"]:
                            if isinstance(content_item, dict):
                                if content_item.get("type") == "output_text":
                                    parts.append(content_item.get("text", ""))
                            elif isinstance(content_item, str):
                                parts.append(content_item)
                    else:
                        text = item.get("content") or item.get("text")
                        if text:
                            parts.append(text)
                elif isinstance(item, str):
                    parts.append(item)
            result = " ".join([p.strip() for p in parts if p]).strip()
            return result or "Groq returned an empty response."

        # Debug fallback for unexpected response structure
        return f"Groq response structure unexpected: {data}"
    except Exception as exc:
        return f"Error communicating with Groq: {str(exc)}"


def get_ai_response(user_message: str, portfolio_context: str, provider: str) -> str:
    """Get AI response based on portfolio context and user query."""
    system_prompt = f"""You are an expert financial advisor specializing in Indian stock markets and portfolio analysis.
You have access to the user's portfolio analysis data and can provide personalized insights, recommendations, and answers to questions about their holdings.

Portfolio Context:
{portfolio_context}

Guidelines:
- Provide specific, actionable insights based on the portfolio data
- Reference specific stocks and their scores when relevant
- Consider risk factors and portfolio diversification
- Be honest about uncertainties and limitations
- Ask clarifying questions if needed to provide better insights
- Focus on long-term investment strategy
- Mention specific metrics like PE ratio, ROE, ROCE when discussing stocks
"""
    messages = [{"role": "user", "content": user_message}]
    if provider == "groq":
        return chat_with_groq(messages, system_prompt)
    return "No AI provider available. Please set GROQ_API_KEY."


def initialize_chat_session():
    """Initialize chat session state in Streamlit."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "portfolio_context" not in st.session_state:
        st.session_state.portfolio_context = ""
    if "ai_provider" not in st.session_state:
        st.session_state.ai_provider = None


def render_chat_interface(results: pd.DataFrame, df: pd.DataFrame) -> None:
    """Render the AI chat assistant interface."""
    initialize_chat_session()
    if not st.session_state.portfolio_context:
        st.session_state.portfolio_context = build_portfolio_context(results, df)
        st.session_state.ai_provider = get_llm_provider()

    st.subheader("🤖 AI Investment Advisor")
    provider = st.session_state.ai_provider
    if not provider:
        st.warning(
            "⚠️ AI Assistant requires an API key. Please set `GROQ_API_KEY` environment variable."
        )
        st.info("Get your API key from [Groq](https://console.groq.com/docs/overview)")
        return

    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    user_input = st.chat_input("Ask me about your portfolio analysis, stock recommendations, or investment strategy...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)

        with st.spinner("Analyzing your portfolio..."):
            response = get_ai_response(
                user_input,
                st.session_state.portfolio_context,
                provider,
            )

        st.session_state.chat_history.append({"role": "assistant", "content": response})
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(response)
