# BGraph

A comprehensive data visualization and analysis tool for exploring relationships between people based on various data sources. Built with Python and Tkinter, this application provides powerful graph visualization, relationship analysis, and data management capabilities.

## Features

### 🎯 Core Functionality
- **Data Import**: Load data from text files or entire folders
- **Smart Parsing**: Automatically extract personal information (names, contacts, documents, etc.)
- **Relationship Mapping**: Visualize connections between people with interactive graphs
- **Advanced Search**: Find people by any data field with powerful search capabilities

### 📊 Visualization
- **Multiple Layout Algorithms**: Force Atlas, Fruchterman-Reingold, and Circular layouts
- **Interactive Graphs**: Pan, zoom, and explore relationships intuitively
- **Custom Styling**: Adjust node sizes, edge widths, and color schemes
- **Dark/Light Themes**: Toggle between different visual themes
- **Cluster Analysis**: Automatic grouping using machine learning (KMeans)

### 🔗 Relationship Analysis
- **Automatic Relationship Detection**: Find connections based on shared data
- **Manual Relationship Management**: Add, edit, and remove connections
- **Path Finding**: Discover shortest paths between any two people
- **Multi-level Exploration**: View first and second-degree connections

### 🤖 AI Integration
- **ChatGPT Analysis**: Get intelligent insights about people and relationships (requires API key)
- **Smart Suggestions**: Automated relationship type detection

### 💾 Data Management
- **Export Options**: Save data as JSON or formatted HTML reports
- **Backup System**: Create and restore from backups
- **Data Merging**: Combine duplicate person records
- **Batch Processing**: Process multiple files simultaneously

## Installation

### Prerequisites
- Python 3.7+
- Required packages:

```bash
pip install tkinter networkx scikit-learn numpy matplotlib geopy openai
```

### Running the Application

```bash
python Bgraph_1415.py
```

## Usage

### Loading Data
1. Use **"Open File"** to load individual text files
2. Use **"Open Folder"** to process all text files in a directory
3. Data is automatically parsed and relationships are established

### Exploring Relationships
1. Select a person from the list to view their details
2. Click **"Show Relations"** to visualize their network
3. Use right-click context menus for advanced operations
4. Navigate the graph with mouse controls:
   - **Left-click + drag**: Pan
   - **Mouse wheel**: Zoom
   - **Right-click**: Context menu

### Advanced Features
- **Search**: Find people by name, phone, email, or any other field
- **Filters**: Sort and group people by various criteria
- **Statistics**: View comprehensive data analytics
- **Map Integration**: Visualize addresses on maps
- **AI Analysis**: Get insights from ChatGPT (set API key first)

## Data Format

The application processes text files with structured sections:

```
=== Section Name ===
Field: Value
Field: Value
...

=== Another Section ===
Field: Value
...
```

Supported fields include:
- Personal information (names, birth dates)
- Contact details (phones, emails, addresses)
- Documents (passports, driver licenses, SNILS, INN)
- Financial data (bank accounts)
- Employment information
- Social media profiles
- Vehicle information

## Configuration

### OpenAI Integration
1. Obtain an API key from OpenAI
2. Enter the key in the settings panel
3. Use the ChatGPT analysis feature for intelligent insights

### Graph Settings
- Adjust node sizes and edge widths
- Choose between different layout algorithms
- Customize color schemes for different relationship types

## Project Structure

- `Person` class: Core data model for storing person information
- `DataVisualizer` class: Main application with GUI and business logic
- Modular components for parsing, visualization, and analysis

## Key Components

### Data Models
- Comprehensive person profiles with multiple data types
- Relationship tracking with metadata
- Source file attribution

### Visualization Engine
- Interactive graph rendering
- Multiple layout algorithms
- Real-time filtering and highlighting

### Analysis Tools
- Statistical reporting
- Cluster analysis
- Path finding algorithms
- AI-powered insights

## Contributing

This is a comprehensive data analysis tool designed for relationship mapping and visualization. Contributions for improving parsing algorithms, visualization techniques, or adding new data sources are welcome.

## License

This project is provided for educational and research purposes. Please ensure compliance with data privacy regulations when using personal information.

## Notes

- The application includes robust error handling and logging
- All operations are logged for audit purposes
- Data is automatically backed up and can be exported in multiple formats
- The interface is in Russian, but the codebase is structured for internationalization

For questions or issues, please refer to the code documentation or contact the development team.
