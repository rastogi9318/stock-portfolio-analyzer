# Indian Stock Portfolio Analyzer

A comprehensive Streamlit-based tool for analyzing Indian stock portfolios with AI-powered investment insights.

## Features

- **Portfolio Upload**: Upload your portfolio via CSV with stock names, quantities, and buying prices
- **Symbol Mapping**: Automatic resolution of company names to NSE symbols (with manual override option)
- **Stock Analysis**: Comprehensive metrics for each stock including:
  - Financial ratios (PE, ROE, ROCE, etc.)
  - Ownership patterns (FII, DII, Promoter holdings)
  - Growth indicators (Sales growth, Profit growth)
  - Technical insights
- **AI Investment Advisor**: Chat with an AI assistant to discuss your portfolio analysis and get personalized investment insights
- **Dashboard Metrics**: 
  - Portfolio value tracking (invested vs current)
  - P&L calculation
  - Average score and recommendation distribution
  - Historical comparisons
- **Export Results**: Download enriched CSV with analysis results

## Installation

Install the dependencies:
```bash
pip install -r requirements.txt
```

## Setup AI Assistant (Optional)

The app includes an AI Investment Advisor powered by **Groq** via the Groq OpenAI-compatible API.

See [AI_SETUP.md](AI_SETUP.md) for detailed setup instructions.

## Usage

Start the app:
```bash
streamlit run app.py
```

1. Upload your portfolio CSV or Excel file
2. Review and edit the symbol mapping if needed
3. Click "Run Analysis" to analyze your portfolio
4. After analysis, use the **AI Investment Advisor** to discuss insights and ask questions about your holdings
5. Download the enriched CSV with analysis results

## Portfolio Input Format

The app now accepts CSV and Excel files and will automatically normalize columns. It keeps only the portfolio fields needed for analysis:
- `stock_name` / `stock` / `name` / `company` / `company_name` / `ticker`
- `quantity` / `qty` / `shares` / `share_count` / `no_of_shares`
- `avg_buy_price` / `average_buy_price` / `buy_price` / `avg_cost` / `cost_price`

If the file contains `buy_value` / `investment_value` / `invested_value`, the app will compute `avg_buy_price` from quantity.

Example:
```
stock_name,quantity,avg_buy_price
Infosys,100,1234.50
TCS,50,3456.78
HDFC Bank,25,1567.89
```

## AI Assistant Examples

Once your analysis is complete, you can ask questions like:

- "Why did INFY get a BUY recommendation?"
- "What's the risk profile of my portfolio?"
- "Should I add more tech stocks?"
- "How does my portfolio compare to market averages?"
- "What's your advice on diversification?"