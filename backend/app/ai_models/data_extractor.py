"""
Reads the law-firm schema for the existing learning pipeline.

SQL uses the new tables. Result columns keep the names the classifier and
locality model already expect (crime_case_id, date_occ, crime_types, and so on).
suspect_count is the opposing-party count. victim_count is the client count.
date_occ is the cause-of-action date. Retrain after loading legal data.
The saved crime-era .pkl files do not apply to this schema.
"""
import pandas as pd
from sqlalchemy import create_engine, text
from typing import Optional, Dict, List
import os
from datetime import datetime, timedelta

class CrimeDataExtractor:
    """Extract and preprocess crime data for ML models"""
    
    def __init__(self, db_url: str):
        """
        Initialize database connection
        
        Args:
            db_url: PostgreSQL connection string
        """
        self.engine = create_engine(db_url)
    
    def get_crime_cases_with_location(self, 
                                      start_date: Optional[str] = None,
                                      end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get all crime cases with location details
        
        Args:
            start_date: Filter from this date (YYYY-MM-DD)
            end_date: Filter until this date (YYYY-MM-DD)
            
        Returns:
            DataFrame with crime case details
        """
        query = """
        SELECT
            cc.case_id AS crime_case_id,
            cc.case_number AS fir_no,
            cc.matter_title AS crime_title,
            cc.matter_description AS crime_description,
            cc.date_cause AS date_occ,
            cc.date_filed AS date_rep,
            cc.status,
            l.location_id,
            l.landmark,
            l.streetno,
            l.pincode,
            pa.city,
            pa.district,
            pa.state,
            (SELECT CONCAT(lw.fname, ' ', lw.lname)
             FROM case_lawyer cl
             JOIN lawyer lw ON cl.lawyer_id = lw.lawyer_id
             WHERE cl.case_id = cc.case_id AND cl.role = 'Lead Counsel' AND cl.end_date IS NULL
             LIMIT 1) AS officer_name,
            (SELECT lw.designation
             FROM case_lawyer cl
             JOIN lawyer lw ON cl.lawyer_id = lw.lawyer_id
             WHERE cl.case_id = cc.case_id AND cl.role = 'Lead Counsel' AND cl.end_date IS NULL
             LIMIT 1) AS officer_rank,
            (SELECT pg.group_name
             FROM case_lawyer cl
             JOIN lawyer lw ON cl.lawyer_id = lw.lawyer_id
             JOIN practice_group pg ON lw.group_id = pg.group_id
             WHERE cl.case_id = cc.case_id AND cl.role = 'Lead Counsel' AND cl.end_date IS NULL
             LIMIT 1) AS dept_name,
            (SELECT STRING_AGG(mt.matter_type, '|')
             FROM matter_type mt
             WHERE mt.case_id = cc.case_id) AS crime_types,
            (SELECT STRING_AGG(ss.statute_section, '|')
             FROM statute_section ss
             WHERE ss.case_id = cc.case_id) AS ipc_sections,
            (SELECT COUNT(*) FROM evidence WHERE case_id = cc.case_id) AS evidence_count,
            (SELECT COUNT(*) FROM case_opposing_party WHERE case_id = cc.case_id) AS suspect_count,
            (SELECT COUNT(*) FROM case_client WHERE case_id = cc.case_id) AS victim_count
        FROM legal_case cc
        LEFT JOIN location l ON cc.location_id = l.location_id
        LEFT JOIN pincode_area pa ON l.pincode = pa.pincode
        WHERE 1=1
        """

        if start_date:
            query += f" AND cc.date_cause >= '{start_date}'"
        if end_date:
            query += f" AND cc.date_cause <= '{end_date}'"

        query += " ORDER BY cc.date_cause DESC"
        
        df = pd.read_sql(query, self.engine)
        
        # Convert dates
        df['date_occ'] = pd.to_datetime(df['date_occ'])
        df['date_rep'] = pd.to_datetime(df['date_rep'])
        
        # Add derived features
        df['report_delay_days'] = (df['date_rep'] - df['date_occ']).dt.days
        df['year'] = df['date_occ'].dt.year
        df['month'] = df['date_occ'].dt.month
        df['day_of_week'] = df['date_occ'].dt.dayofweek
        df['day_of_month'] = df['date_occ'].dt.day
        df['quarter'] = df['date_occ'].dt.quarter
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        return df
    
    def get_location_crime_counts(self) -> pd.DataFrame:
        """
        Get crime counts by location for hotspot analysis
        
        Returns:
            DataFrame with location-wise crime statistics
        """
        query = """
        SELECT 
            l.location_id,
            l.landmark,
            l.pincode,
            pa.city,
            pa.district,
            pa.state,
            COUNT(cc.case_id) as total_crimes,
            COUNT(CASE WHEN cc.status = 'Filed' THEN 1 END) as open_cases,
            COUNT(CASE WHEN cc.status = 'Disposed' THEN 1 END) as closed_cases,
            COUNT(CASE WHEN cc.status = 'Hearing' THEN 1 END) as under_investigation,
            STRING_AGG(DISTINCT mt.matter_type, '|') as crime_types,
            MIN(cc.date_cause) as first_crime_date,
            MAX(cc.date_cause) as last_crime_date
        FROM location l
        JOIN pincode_area pa ON l.pincode = pa.pincode
        LEFT JOIN legal_case cc ON l.location_id = cc.location_id
        LEFT JOIN matter_type mt ON cc.case_id = mt.case_id
        GROUP BY l.location_id, l.landmark, l.pincode, pa.city, pa.district, pa.state
        HAVING COUNT(cc.case_id) > 0
        ORDER BY total_crimes DESC
        """
        
        df = pd.read_sql(query, self.engine)
        df['first_crime_date'] = pd.to_datetime(df['first_crime_date'])
        df['last_crime_date'] = pd.to_datetime(df['last_crime_date'])
        df['days_span'] = (df['last_crime_date'] - df['first_crime_date']).dt.days
        df['crime_frequency'] = df['total_crimes'] / (df['days_span'] + 1)
        
        return df
    
    def get_time_series_data(self, 
                            frequency: str = 'D',
                            location_id: Optional[int] = None,
                            crime_type: Optional[str] = None) -> pd.DataFrame:
        """
        Get time series data for forecasting
        
        Args:
            frequency: 'D' (daily), 'W' (weekly), 'M' (monthly)
            location_id: Filter by specific location
            crime_type: Filter by specific crime type
            
        Returns:
            DataFrame with time series of crime counts
        """
        query = """
        SELECT
            cc.date_filed AS date_occ,
            COUNT(*) as crime_count,
            STRING_AGG(DISTINCT mt.matter_type, '|') as crime_types
        FROM legal_case cc
        LEFT JOIN matter_type mt ON cc.case_id = mt.case_id
        WHERE 1=1
        """

        if location_id:
            query += f" AND cc.location_id = {location_id}"
        if crime_type:
            query += f" AND EXISTS (SELECT 1 FROM matter_type WHERE case_id = cc.case_id AND matter_type = '{crime_type}')"

        query += " GROUP BY cc.date_filed ORDER BY cc.date_filed"
        
        df = pd.read_sql(query, self.engine)
        df['date_occ'] = pd.to_datetime(df['date_occ'])
        df.set_index('date_occ', inplace=True)
        
        # Resample to desired frequency
        if frequency == 'D':
            df_resampled = df.resample('D').agg({
                'crime_count': 'sum',
                'crime_types': lambda x: '|'.join(filter(None, x))
            })
        elif frequency == 'W':
            df_resampled = df.resample('W').agg({
                'crime_count': 'sum',
                'crime_types': lambda x: '|'.join(filter(None, x))
            })
        elif frequency == 'M':
            df_resampled = df.resample('ME').agg({
                'crime_count': 'sum',
                'crime_types': lambda x: '|'.join(filter(None, x))
            })
        else:
            df_resampled = df
        
        # Fill missing dates with 0
        df_resampled['crime_count'] = df_resampled['crime_count'].fillna(0).astype(int)
        
        return df_resampled.reset_index()
    
    def get_crime_type_features(self) -> pd.DataFrame:
        """
        Get features for crime type classification
        
        Returns:
            DataFrame with features for each crime case
        """
        query = """
        SELECT
            cc.case_id AS crime_case_id,
            cc.matter_description AS crime_description,
            cc.date_cause AS date_occ,
            cc.status,
            l.pincode,
            pa.city,
            pa.district,
            EXTRACT(HOUR FROM cc.date_cause::timestamp) as hour_of_day,
            EXTRACT(DOW FROM cc.date_cause) as day_of_week,
            EXTRACT(MONTH FROM cc.date_cause) as month,
            (SELECT COUNT(*) FROM evidence WHERE case_id = cc.case_id) as evidence_count,
            (SELECT COUNT(*) FROM case_opposing_party WHERE case_id = cc.case_id) as suspect_count,
            (SELECT COUNT(*) FROM case_client WHERE case_id = cc.case_id) as victim_count,
            (SELECT STRING_AGG(mt.matter_type, '|')
             FROM matter_type mt
             WHERE mt.case_id = cc.case_id) as crime_types
        FROM legal_case cc
        LEFT JOIN location l ON cc.location_id = l.location_id
        LEFT JOIN pincode_area pa ON l.pincode = pa.pincode
        WHERE EXISTS (SELECT 1 FROM matter_type WHERE case_id = cc.case_id)
        """
        
        df = pd.read_sql(query, self.engine)
        df['date_occ'] = pd.to_datetime(df['date_occ'])
        
        return df
    
    def get_suspect_patterns(self) -> pd.DataFrame:
        """
        Get suspect patterns for analysis
        
        Returns:
            DataFrame with suspect information
        """
        query = """
        SELECT
            s.party_id AS suspect_id,
            s.fname,
            s.lname,
            s.sex,
            s.repeat_party AS hascriminalrec,
            COUNT(DISTINCT cop.case_id) as case_count,
            STRING_AGG(DISTINCT mt.matter_type, '|') as crime_types_involved,
            MIN(cc.date_cause) as first_case_date,
            MAX(cc.date_cause) as last_case_date,
            STRING_AGG(DISTINCT pa.city, '|') as cities_involved
        FROM opposing_party s
        JOIN case_opposing_party cop ON s.party_id = cop.party_id
        JOIN legal_case cc ON cop.case_id = cc.case_id
        LEFT JOIN matter_type mt ON cc.case_id = mt.case_id
        LEFT JOIN location l ON cc.location_id = l.location_id
        LEFT JOIN pincode_area pa ON l.pincode = pa.pincode
        GROUP BY s.party_id, s.fname, s.lname, s.sex, s.repeat_party
        """
        
        df = pd.read_sql(query, self.engine)
        df['first_case_date'] = pd.to_datetime(df['first_case_date'])
        df['last_case_date'] = pd.to_datetime(df['last_case_date'])
        df['days_active'] = (df['last_case_date'] - df['first_case_date']).dt.days
        
        return df
    
    def close(self):
        """Close database connection"""
        self.engine.dispose()


# Example usage
if __name__ == "__main__":
    # Database connection
    DB_URL = os.getenv("DATABASE_URL", "")
    
    extractor = CrimeDataExtractor(DB_URL)
    
    # Get crime cases
    print("Fetching crime cases...")
    df_crimes = extractor.get_crime_cases_with_location()
    print(f"Total cases: {len(df_crimes)}")
    print(df_crimes.head())
    
    # Get location hotspots
    print("\nFetching location hotspots...")
    df_locations = extractor.get_location_crime_counts()
    print(f"Total locations: {len(df_locations)}")
    print(df_locations.head())
    
    # Get time series
    print("\nFetching time series...")
    df_ts = extractor.get_time_series_data(frequency='M')
    print(f"Time periods: {len(df_ts)}")
    print(df_ts.head())
    
    extractor.close()