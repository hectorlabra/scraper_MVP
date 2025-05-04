import pandas as pd
import logging
from typing import List, Dict, Any, Optional, Tuple, Set, Union

logger = logging.getLogger(__name__)

class DeduplicationProcessor:
    """
    Specialized class for identifying and removing duplicate leads
    with advanced exact and fuzzy matching capabilities.
    """

    def __init__(self, data: pd.DataFrame):
        """
        Initializes the DeduplicationProcessor with a pandas DataFrame.

        Args:
            data (pd.DataFrame): The input DataFrame containing scraped leads.
                                 Expected columns might include 'business_name', 
                                 'phone', 'email', 'location', etc.
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Input data must be a pandas DataFrame.")
        self.data = data.copy()  # Work on a copy to avoid modifying original
        self.original_row_count = len(self.data)
        logger.info(f"DeduplicationProcessor initialized with {self.original_row_count} records")

    def _calculate_completeness(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculates a completeness score for each row (count of non-null values).

        Args:
            df (pd.DataFrame): DataFrame to calculate completeness for

        Returns:
            pd.Series: Series containing completeness scores for each row
        """
        return df.notna().sum(axis=1)

    def _validate_subset_columns(self, subset: List[str]) -> List[str]:
        """
        Validates that the subset columns exist in the DataFrame.

        Args:
            subset (List[str]): List of column names to validate

        Returns:
            List[str]: List of valid column names found in the DataFrame

        Raises:
            ValueError: If none of the specified columns are found in the DataFrame
        """
        if not subset:
            logger.warning("No subset provided for deduplication.")
            return []
            
        valid_subset = [col for col in subset if col in self.data.columns]
        
        if not valid_subset:
            raise ValueError(f"None of the subset columns {subset} found in the DataFrame.")
        
        invalid_columns = set(subset) - set(valid_subset)
        if invalid_columns:
            logger.warning(f"Columns {invalid_columns} not found and will be ignored.")
            
        return valid_subset

    def deduplicate_exact(self, subset: List[str], keep_most_complete: bool = True) -> pd.DataFrame:
        """
        Performs deduplication based on exact matches in specified columns.

        Args:
            subset (List[str]): List of column names to consider for identifying duplicates.
                                E.g., ['business_name', 'phone', 'email']
            keep_most_complete (bool): If True, keeps the duplicate record with the most 
                                      non-null values. If False, keeps the first occurrence.

        Returns:
            pd.DataFrame: The DataFrame with exact duplicates removed.
        """
        valid_subset = self._validate_subset_columns(subset)
        
        if not valid_subset:
            logger.warning("No valid columns for exact deduplication. Returning original data.")
            return self.data.copy()

        # Create a temporary copy of the data for processing
        temp_df = self.data.copy()
        
        if keep_most_complete:
            # Calculate completeness score before dropping duplicates
            temp_df['_completeness'] = self._calculate_completeness(temp_df)
            
            # Sort by completeness (descending) so the most complete comes first within a duplicate group
            # Use reset_index to create a temporary column for stable sorting
            temp_df = temp_df.reset_index(drop=False)
            temp_df = temp_df.sort_values(by=['_completeness', 'index'], ascending=[False, True])
            
            # Drop duplicates, keeping the first (which is the most complete due to sorting)
            deduplicated_df = temp_df.drop_duplicates(subset=valid_subset, keep='first')
            
            # Remove the temporary columns
            if 'index' in deduplicated_df.columns:
                deduplicated_df = deduplicated_df.set_index('index')
            deduplicated_df = deduplicated_df.drop(columns=['_completeness'])
            
        else:
            # Standard drop_duplicates, keeping the first occurrence
            deduplicated_df = temp_df.drop_duplicates(subset=valid_subset, keep='first')

        removed_count = len(self.data) - len(deduplicated_df)
        logger.info(f"Exact deduplication complete. Removed {removed_count} duplicates based on {valid_subset}.")
        
        # Update the internal data
        self.data = deduplicated_df 
        
        return self.data.copy()

    # --- Fuzzy Matching Methods ---

    def deduplicate_fuzzy(self, column: str, threshold: int = 80, keep_most_complete: bool = True, 
                         additional_exact_columns: List[str] = None) -> pd.DataFrame:
        """
        Performs deduplication based on fuzzy matching in a specified column,
        optionally combined with exact matching on additional columns.

        Args:
            column (str): The column name to use for fuzzy matching (typically 'business_name')
            threshold (int): The similarity threshold (0-100) for fuzzy matching (default: 80)
            keep_most_complete (bool): If True, keeps the record with the most non-null values
                                      when duplicates are found (default: True)
            additional_exact_columns (List[str]): Optional list of columns that must match exactly
                                                 in addition to the fuzzy match (e.g., ['location'])

        Returns:
            pd.DataFrame: The DataFrame with fuzzy-matched duplicates removed

        Note:
            This method requires the fuzzywuzzy package. Install with:
            pip install fuzzywuzzy python-Levenshtein
        """
        try:
            from fuzzywuzzy import fuzz
        except ImportError:
            logger.error("fuzzywuzzy package not found. Install with: pip install fuzzywuzzy python-Levenshtein")
            raise ImportError("fuzzywuzzy package is required for fuzzy matching")

        # Validate column exists
        if column not in self.data.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")
            
        # Validate additional exact columns if provided
        exact_columns = []
        if additional_exact_columns:
            exact_columns = self._validate_subset_columns(additional_exact_columns)

        # Create a temporary copy and fill NAs in the fuzzy match column to avoid errors
        temp_df = self.data.copy()
        temp_df[column] = temp_df[column].fillna("")
        
        # Calculate completeness score for later use if needed
        if keep_most_complete:
            temp_df['_completeness'] = self._calculate_completeness(temp_df)

        # Group by exact columns first if provided to reduce comparison scope
        if exact_columns:
            # We'll process each group separately and concatenate results
            groups = []
            for name, group in temp_df.groupby(exact_columns):
                # Skip groups with only one record (no duplicates possible)
                if len(group) <= 1:
                    groups.append(group)
                    continue
                
                # Process this group for fuzzy duplicates
                processed_group = self._process_fuzzy_group(group, column, threshold, keep_most_complete)
                groups.append(processed_group)
            
            # Combine all processed groups
            deduplicated_df = pd.concat(groups, ignore_index=False)
        else:
            # Process entire dataframe if no exact columns provided
            deduplicated_df = self._process_fuzzy_group(temp_df, column, threshold, keep_most_complete)
        
        # Remove the temporary completeness column if it exists
        if keep_most_complete and '_completeness' in deduplicated_df.columns:
            deduplicated_df = deduplicated_df.drop(columns=['_completeness'])

        removed_count = len(self.data) - len(deduplicated_df)
        logger.info(f"Fuzzy deduplication complete. Removed {removed_count} duplicates with threshold {threshold}.")
        
        # Update the internal data
        self.data = deduplicated_df
        
        return self.data.copy()

    def _process_fuzzy_group(self, group_df: pd.DataFrame, column: str, threshold: int, 
                            keep_most_complete: bool) -> pd.DataFrame:
        """
        Process a group of records for fuzzy matching.
        
        Args:
            group_df: DataFrame group to process
            column: Column name to use for fuzzy matching
            threshold: Similarity threshold (0-100)
            keep_most_complete: Whether to keep most complete records
            
        Returns:
            DataFrame with fuzzy duplicates removed
        """
        from fuzzywuzzy import fuzz
        
        # Create a duplicate tracking set (indices to remove)
        to_remove = set()
        
        # Get the index and values as lists for easier processing
        indices = group_df.index.tolist()
        values = group_df[column].tolist()
        
        # Compare each value with all others
        for i in range(len(indices)):
            # Skip if this index is already marked for removal
            if indices[i] in to_remove:
                continue
                
            val1 = values[i]
            if not val1:  # Skip empty values
                continue
                
            # Compare with all subsequent values
            for j in range(i + 1, len(indices)):
                # Skip if this index is already marked for removal
                if indices[j] in to_remove:
                    continue
                    
                val2 = values[j]
                if not val2:  # Skip empty values
                    continue
                
                # Calculate similarity score
                similarity = fuzz.ratio(val1, val2)
                
                # If similarity exceeds threshold, mark as duplicate
                if similarity >= threshold:
                    # Determine which record to keep
                    if keep_most_complete:
                        # Get completeness scores
                        score_i = group_df.loc[indices[i], '_completeness']
                        score_j = group_df.loc[indices[j], '_completeness']
                        
                        # Mark the less complete record for removal
                        if score_i >= score_j:
                            to_remove.add(indices[j])
                        else:
                            to_remove.add(indices[i])
                            # No need to continue comparing i if it's being removed
                            break
                    else:
                        # Always keep the first occurrence
                        to_remove.add(indices[j])
        
        # Create a mask for records to keep
        mask = ~group_df.index.isin(to_remove)
        
        # Return the filtered DataFrame
        return group_df[mask]

    # --- Configurable Rules Interface ---

    def deduplicate(self, rules: List[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Performs deduplication based on a set of configurable rules.

        Args:
            rules (List[Dict[str, Any]]): List of rule dictionaries. Each rule can contain:
                - 'type': 'exact' or 'fuzzy'
                - 'columns' or 'column': List of columns for exact matching, or single column for fuzzy
                - 'threshold': For fuzzy matching (default: 80)
                - 'keep_most_complete': Whether to keep the most complete record (default: True)
                - 'operator': 'AND' or 'OR' to define how to combine with the next rule
                              (ignored for the last rule)

        Returns:
            pd.DataFrame: The DataFrame with duplicates removed according to rules

        Example rules:
            [
                {'type': 'exact', 'columns': ['email'], 'operator': 'OR'},
                {'type': 'exact', 'columns': ['phone']},
                {'type': 'fuzzy', 'column': 'business_name', 'threshold': 85, 'additional_exact': ['location']}
            ]
            
        Note:
            If no rules are provided, a default rule set will be applied, which looks for exact
            matches on ['email', 'phone'] or fuzzy matches on 'business_name' with a threshold of 80.
        """
        # Default rules if none provided
        if not rules:
            rules = [
                {'type': 'exact', 'columns': ['email'], 'operator': 'OR'},
                {'type': 'exact', 'columns': ['phone'], 'operator': 'OR'},
                {'type': 'fuzzy', 'column': 'business_name', 'threshold': 80}
            ]
            
        # Clone original data
        original_data = self.data.copy()
        processed_dfs = []
        
        # Process each rule sequentially
        for i, rule in enumerate(rules):
            rule_type = rule.get('type', 'exact')
            operator = rule.get('operator', 'AND').upper()
            keep_most_complete = rule.get('keep_most_complete', True)
            
            # Clone original data as starting point for this rule
            self.data = original_data.copy()
            
            try:
                if rule_type == 'exact':
                    columns = rule.get('columns', [])
                    if not columns:
                        logger.warning(f"Rule {i+1}: No columns specified for exact matching. Skipping.")
                        continue
                        
                    result_df = self.deduplicate_exact(columns, keep_most_complete)
                
                elif rule_type == 'fuzzy':
                    column = rule.get('column')
                    if not column:
                        logger.warning(f"Rule {i+1}: No column specified for fuzzy matching. Skipping.")
                        continue
                        
                    threshold = rule.get('threshold', 80)
                    additional_exact = rule.get('additional_exact', [])
                    
                    result_df = self.deduplicate_fuzzy(
                        column, threshold, keep_most_complete, additional_exact
                    )
                    
                else:
                    logger.warning(f"Rule {i+1}: Unknown rule type '{rule_type}'. Skipping.")
                    continue
                    
                processed_dfs.append(result_df)
                
                # Log what was done
                logger.info(f"Rule {i+1} ({rule_type}) applied: {len(original_data) - len(result_df)} duplicates removed")
                
            except Exception as e:
                logger.error(f"Error applying rule {i+1}: {e}")
                # Continue with next rule
        
        # Combine results based on operators
        if not processed_dfs:
            logger.warning("No valid rules applied. Returning original data.")
            return original_data
        
        # Start with the first result
        final_df = processed_dfs[0]
        
        # Apply operators to combine results
        for i in range(len(rules) - 1):
            if i >= len(processed_dfs) - 1:
                break
                
            operator = rules[i].get('operator', 'AND').upper()
            
            if operator == 'OR':
                # Union of both results (keep records that survived in either result)
                indices = set(final_df.index) | set(processed_dfs[i+1].index)
                final_df = original_data.loc[list(indices)]
            else:  # AND or any other value
                # Intersection (only keep records that survived in both results)
                indices = set(final_df.index) & set(processed_dfs[i+1].index)
                final_df = original_data.loc[list(indices)]
        
        # Update instance data with final result
        self.data = final_df
        
        removed_count = len(original_data) - len(final_df)
        logger.info(f"Combined deduplication complete. Removed {removed_count} records in total.")
        
        return self.data.copy()

    # --- Utility Methods ---

    def get_data(self) -> pd.DataFrame:
        """Returns the current state of the DataFrame."""
        return self.data.copy()
        
    def get_deduplication_stats(self) -> Dict[str, int]:
        """
        Returns statistics about the deduplication process.
        
        Returns:
            Dict containing original count, current count, and records removed
        """
        current_count = len(self.data)
        removed = self.original_row_count - current_count
        return {
            'original_count': self.original_row_count,
            'current_count': current_count,
            'removed_count': removed,
            'removed_percentage': round((removed / self.original_row_count) * 100, 2) if self.original_row_count > 0 else 0
        }
        
    def reset(self) -> None:
        """
        Resets the processor to its original state.
        This allows trying different deduplication strategies on the same data.
        """
        self.data = self._original_data.copy() if hasattr(self, '_original_data') else self.data
        logger.info("Processor reset to original state")
        
    def save_original(self) -> None:
        """
        Saves the current state as original data.
        Allows multiple deduplication attempts without re-initializing.
        """
        self._original_data = self.data.copy()
        self.original_row_count = len(self._original_data)
        logger.info(f"Saved current state as original ({self.original_row_count} records)")
        
    def to_csv(self, filepath: str, **kwargs) -> None:
        """
        Save the deduplicated data to a CSV file.
        
        Args:
            filepath: Path to save the CSV file
            **kwargs: Additional arguments to pass to pandas.DataFrame.to_csv()
        """
        self.data.to_csv(filepath, **kwargs)
        logger.info(f"Saved {len(self.data)} deduplicated records to {filepath}")
        
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """
        Convert the deduplicated data to a list of dictionaries.
        
        Returns:
            List of dictionaries containing the deduplicated data
        """
        return self.data.to_dict(orient='records')


# Example Usage (Optional - for testing during development)
if __name__ == '__main__':
    # Sample Data with duplicates and near-duplicates
    data = {
        'business_name': ['Cafe Alpha', 'Cafe Alpha', 'Restaurant Beta', 'CAFE ALPHA', 'Restaurant Beta', 'Hotel Gamma'],
        'phone': ['123-456', '123-456', '789-012', '123-456', None, '321-654'],
        'email': ['alpha@test.com', None, 'beta@test.com', 'alpha@test.com', 'beta@test.com', 'gamma@test.com'],
        'location': ['City A', 'City A', 'City B', 'City A', 'City B', 'City C'],
        'extra_info': [None, 'Has Wifi', 'Good Food', 'Opened 2023', '5 stars', 'Pool available']
    }
    df = pd.DataFrame(data)
    
    print("Original DataFrame:")
    print(df)
    print("-" * 50)

    # --- Test Exact Deduplication ---
    processor = DeduplicationProcessor(df)
    processor.save_original()  # Save state for reuse
    
    print("\nExact Deduplication - Name & Phone:")
    deduped_df = processor.deduplicate_exact(subset=['business_name', 'phone'])
    print(deduped_df)
    print("Stats:", processor.get_deduplication_stats())
    print("-" * 50)

    # Reset and try different fields
    processor.reset()
    print("\nExact Deduplication - Email only:")
    deduped_df = processor.deduplicate_exact(subset=['email'])
    print(deduped_df)
    print("Stats:", processor.get_deduplication_stats())
    print("-" * 50)

    # --- Test Fuzzy Matching ---
    processor.reset()
    print("\nFuzzy Deduplication - Business Name:")
    try:
        deduped_df = processor.deduplicate_fuzzy(column='business_name', threshold=75)
        print(deduped_df)
        print("Stats:", processor.get_deduplication_stats())
    except ImportError:
        print("Skipping fuzzy test - fuzzywuzzy not installed")
    print("-" * 50)

    # --- Test Configurable Rules ---
    processor.reset()
    print("\nConfigurable Rules Deduplication:")
    rules = [
        {'type': 'exact', 'columns': ['email'], 'operator': 'OR'},
        {'type': 'exact', 'columns': ['phone', 'location']}
    ]
    deduped_df = processor.deduplicate(rules=rules)
    print(deduped_df)
    print("Stats:", processor.get_deduplication_stats())
    print("-" * 50)
