# IIT BHU Project Workspace

This repository contains two main projects developed for the IIT BHU Hackathon:

1.  **[Epidemic Spread Prediction](file:///Epidemic_Spread_Prediction/README.md)**: A Machine Learning pipeline for predicting infectious disease trends.
2.  **[techsta](file:///techsta/readme.md)**: A web-based platform (Frontend, Backend, and RAG services).

---

## 🚀 Getting Started

Since this repository excludes large environment files and raw data to stay lightweight, follow these steps after cloning:

### 1. Epidemic Spread Prediction (Python/ML)
Navigate to the ML project folder:
```bash
cd Epidemic_Spread_Prediction
```

*   **Set up Virtual Environment:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # Windows
    # source venv/bin/activate # Linux/Mac
    ```
*   **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
*   **Download Data:**
    Since raw data is ignored by Git, you must run the collection script first:
    ```bash
    python notebooks/01_data_collection.py
    ```

### 2. Techsta (Web/App)
Navigate to the web project components:

*   **Frontend:**
    ```bash
    cd techsta/frontend
    npm install
    npm run dev
    ```
*   **Backend:**
    ```bash
    cd ../backend
    npm install
    npm run dev
    ```

---

## 🛠️ Repository Structure
- `Epidemic_Spread_Prediction/`: Core ML logic, notebooks, and prediction models.
- `techsta/`: Full-stack application components including AI agents and RAG services.
- `.gitignore`: Configured to keep the repository clean of environment bloat and large datasets.

---
*Built by Team Techsta for IIT BHU.*
