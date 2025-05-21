import pandas as pd
import io

def load_data(file_object):
    """
    Load data from CSV or Excel file
    
    Args:
        file_object: File object from streamlit uploader or file path
        
    Returns:
        pandas DataFrame with the loaded data
    """
    if isinstance(file_object, str):
        # It's a file path
        if file_object.endswith('.csv'):
            return pd.read_csv(file_object)
        elif file_object.endswith(('.xlsx', '.xls')):
            return pd.read_excel(file_object)
    else:
        # It's a file-like object from streamlit
        if hasattr(file_object, 'name'):
            if file_object.name.endswith('.csv'):
                return pd.read_csv(file_object)
            elif file_object.name.endswith(('.xlsx', '.xls')):
                return pd.read_excel(file_object)
        
    # Try to infer the file type
    try:
        return pd.read_csv(file_object)
    except:
        try:
            return pd.read_excel(file_object)
        except Exception as e:
            raise ValueError(f"Unsupported file format: {str(e)}")

def validate_equipment_data(df):
    """
    Validate incoming equipment data
    
    Args:
        df: pandas DataFrame containing equipment data
        
    Returns:
        Validated pandas DataFrame with potential issues flagged
    """
    required_fields = ['Unit #', 'Description']
    recommended_fields = ['Year', 'Location', 'Condition']
    
    # Check for missing required fields
    missing_required = [field for field in required_fields if field not in df.columns]
    if missing_required:
        raise ValueError(f"Missing required fields: {missing_required}")
    
    # Flag missing recommended fields
    missing_recommended = [field for field in recommended_fields if field not in df.columns]
    if missing_recommended:
        print(f"Warning: Missing recommended fields: {missing_recommended}")
    
    # Make a copy to avoid SettingWithCopyWarning
    df = df.copy()
    
    # Normalize data
    if 'Year' in df.columns:
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        
    # Identify potential data issues
    df['validation_issues'] = df.apply(identify_data_issues, axis=1)
    
    return df

def identify_data_issues(row):
    """
    Identify potential issues with an equipment entry
    
    Args:
        row: DataFrame row with equipment data
        
    Returns:
        List of issue descriptions, empty if no issues
    """
    issues = []
    
    # Check for missing values in important fields
    for field in ['Description', 'Year', 'Condition']:
        if field in row and pd.isna(row[field]):
            issues.append(f"Missing {field}")
    
    # Check for potentially invalid years
    if 'Year' in row and not pd.isna(row['Year']):
        year = row['Year']
        current_year = pd.Timestamp.now().year
        if year < 1900 or year > current_year + 1:
            issues.append(f"Questionable year: {year}")
    
    # Check for minimal description
    if 'Description' in row and not pd.isna(row['Description']):
        if len(str(row['Description'])) < 5:
            issues.append("Description too short")
    
    return issues

def clean_data(df):
    """
    Clean and standardize equipment data
    
    Args:
        df: pandas DataFrame with equipment data
        
    Returns:
        Cleaned pandas DataFrame
    """
    df = df.copy()
    
    # Fill common missing values
    if 'Condition' in df.columns:
        df['Condition'] = df['Condition'].fillna('Unknown')
    
    if 'Location' in df.columns:
        df['Location'] = df['Location'].fillna('Unspecified')
    
    # Standardize condition values
    if 'Condition' in df.columns:
        # Map various condition descriptions to standard values
        condition_mapping = {
            'excellent': 'Excellent',
            'exc': 'Excellent',
            'good': 'Good',
            'fair': 'Fair',
            'poor': 'Poor',
            'broken': 'Poor',
            'damaged': 'Poor',
            'new': 'Excellent',
            'like new': 'Excellent',
            'used': 'Good',
            'working': 'Good',
            'non-working': 'Poor',
            'non working': 'Poor',
            'unknown': 'Unknown'
        }
        
        df['Condition'] = df['Condition'].str.lower().map(
            lambda x: next((v for k, v in condition_mapping.items() if k in str(x).lower()), x)
        )
    
    # Convert year to integer if possible
    if 'Year' in df.columns:
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        df['Year'] = df['Year'].fillna(0).astype(int)
        # Set 0 years back to NaN for display
        df.loc[df['Year'] == 0, 'Year'] = None
    
    return df