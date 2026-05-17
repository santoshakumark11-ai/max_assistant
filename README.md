# 🚀 App Title
Simple Q&A Assistance for IBM Maximo

## ✨ Features
* **Real-time Processing**: Clarify user queries.
* **MCP Server**: Fast MCP Server.
* **AI Powered**: Use gpt-5-mini LLM model for reasoning.

## 🛠️ Local Setup
1. **Clone the repo**
   ```bash
   git clone https://github.com
   cd repo
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```text
   OPENAI_API_KEY=your_key_here
   MAXIMO_BASE_URL=https://<maximo host>/maximo/api
   MAXIMO_API_KEY=maxadmin api key

   ```

4. **Run the app**
   ```bash
   streamlit run app.py
   ```

## 📦 Requirements
* mcp[cli]>=1.2.0
* openai>=1.0.0
* python-dotenv>=0.19.0
* requests>=2.25.0
* streamlit>=1.0.0
* httpx>=0.24.0