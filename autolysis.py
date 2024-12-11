# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "openai",
#   "pandas",
#   "numpy",
#   "seaborn",
#   "matplotlib",
# ]
# ///

import os
import sys
import json
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import requests

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
API_TOKEN = os.getenv('AIPROXY_TOKEN')

# Verify that the API token is available
if not API_TOKEN:
    print("Error: AIPROXY_TOKEN environment variable not set.")
    sys.exit(1)

# Headers for the API request
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_TOKEN}"
}

def load_dataset(file_path):
    """
    Load the dataset from a CSV file.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Loaded DataFrame.
    """
    try:
        data = pd.read_csv(file_path, encoding='latin1')
        print(f"Dataset loaded successfully: {file_path}")
        return data
    except Exception as e:
        print(f"Failed to load dataset: {e}")
        sys.exit(1)

def analyze_data(data):
    """
    Perform comprehensive analysis on the dataset.

    Args:
        data (pd.DataFrame): The dataset to analyze.

    Returns:
        dict: Dictionary containing analysis results.
    """
    analysis = {}
    try:
        # Basic information
        analysis["shape"] = data.shape
        analysis["columns"] = data.dtypes.apply(lambda x: x.name).to_dict()
        analysis["missing_values"] = data.isnull().sum().to_dict()
        analysis["summary_statistics"] = data.describe(include='all').to_dict()

        # Advanced analysis
        numeric_data = data.select_dtypes(include='number')
        if not numeric_data.empty:
            analysis["correlation_matrix"] = numeric_data.corr().to_dict()
            # Outlier detection using IQR
            Q1 = numeric_data.quantile(0.25)
            Q3 = numeric_data.quantile(0.75)
            IQR = Q3 - Q1
            outlier_condition = ((numeric_data < (Q1 - 1.5 * IQR)) | (numeric_data > (Q3 + 1.5 * IQR)))
            outliers = numeric_data[outlier_condition]
            analysis["outliers"] = outliers.dropna(how='all').to_dict(orient='records')
    except Exception as e:
        print(f"Error during analysis: {e}")
    return analysis

def visualize_data(data, output_dir):
    """
    Create visualizations for the dataset.

    Args:
        data (pd.DataFrame): The dataset to visualize.
        output_dir (str): Directory to save the visualizations.

    Returns:
        list: List of file paths to the generated charts.
    """
    os.makedirs(output_dir, exist_ok=True)
    charts = []
    try:
        numeric_data = data.select_dtypes(include='number')
        # Limit to 3 numeric columns for visualization
        columns_to_plot = numeric_data.columns[:3]
        for col in columns_to_plot:
            plt.figure(figsize=(6, 6))
            sns.histplot(numeric_data[col].dropna(), kde=True, color='blue')
            plt.title(f'Distribution of {col}', fontsize=14)
            plt.xlabel(col, fontsize=12)
            plt.ylabel('Frequency', fontsize=12)
            plt.tight_layout()
            chart_path = os.path.join(output_dir, f'{col}_distribution.png')
            plt.savefig(chart_path, dpi=100)
            plt.close()
            charts.append(chart_path)
        # Correlation heatmap
        if numeric_data.shape[1] > 1:
            plt.figure(figsize=(6, 6))
            sns.heatmap(numeric_data.corr(), annot=True, cmap='coolwarm', square=True)
            plt.title('Correlation Matrix', fontsize=14)
            plt.tight_layout()
            chart_path = os.path.join(output_dir, 'correlation_matrix.png')
            plt.savefig(chart_path, dpi=100)
            plt.close()
            charts.append(chart_path)
    except Exception as e:
        print(f"Visualization error: {e}")
    return charts

def generate_narrative(analysis, charts):
    """
    Generate a narrative summary using LLM via AI Proxy.

    Args:
        analysis (dict): Dictionary containing analysis results.
        charts (list): List of file paths to the generated charts.

    Returns:
        str: Generated narrative.
    """
    try:
        # Craft a concise and context-rich prompt
        prompt = (
            "You are an expert data analyst. Based on the following dataset analysis, "
            "generate a comprehensive report with insights and implications.\n\n"
            "### Dataset Structure\n"
            f"- Shape: {analysis['shape']}\n"
            f"- Columns:\n{json.dumps(analysis['columns'], indent=2)}\n"
            f"- Missing Values:\n{json.dumps(analysis['missing_values'], indent=2)}\n\n"
            "### Summary Statistics\n"
            f"{json.dumps(analysis['summary_statistics'], indent=2)}\n"
        )
        if "correlation_matrix" in analysis:
            prompt += (
                "\n### Correlation Matrix\n"
                f"{json.dumps(analysis['correlation_matrix'], indent=2)}\n"
            )
        if "outliers" in analysis and analysis["outliers"]:
            prompt += "\n### Detected Outliers\nSome data points may be outliers based on the IQR method.\n"

        prompt += (
            "\nUse the provided visualizations to enhance your explanations. "
            "Structure the report with markdown headings for clarity."
        )

        # Prepare the payload for the API request
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.7,
        }

        response = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload))

        if response.status_code == 200:
            response_json = response.json()
            return response_json['choices'][0]['message']['content'].strip()
        else:
            print(f"API request failed: {response.status_code} - {response.text}")
            sys.exit(1)

    except Exception as e:
        print(f"Error during narrative generation: {e}")
        sys.exit(1)

def save_report(narrative, charts, output_dir):
    """
    Save the generated narrative and visualizations into a README.md file.

    Args:
        narrative (str): The generated narrative.
        charts (list): List of file paths to the generated charts.
        output_dir (str): Directory to save the report.
    """
    try:
        readme_path = os.path.join(output_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write("# Analysis Report\n\n")
            f.write(narrative + "\n\n")
            for chart in charts:
                relative_path = os.path.basename(chart)
                f.write(f"![{relative_path}]({relative_path})\n\n")
        print(f"Report saved at: {readme_path}")
    except Exception as e:
        print(f"Error saving report: {e}")

def main(file_path):
    """
    Main function to execute the data analysis workflow.

    Args:
        file_path (str): Path to the input CSV file.
    """
    output_dir = os.path.splitext(os.path.basename(file_path))[0]
    data = load_dataset(file_path)
    analysis = analyze_data(data)
    charts = visualize_data(data, output_dir)
    narrative = generate_narrative(analysis, charts)
    save_report(narrative, charts, output_dir)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py <dataset.csv>")
        sys.exit(1)
    main(sys.argv[1])