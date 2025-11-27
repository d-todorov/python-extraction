"""
Example Usage of Exchange Rate API Client

This script demonstrates how to use the ExchangeRateClient class
to fetch exchange rates with caching and error handling.

Author: API Integration
Date: 2025-11-25
"""

from api_client import ExchangeRateClient
import time


def example_basic_usage():
    """Example 1: Basic usage - fetch specific currencies."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    # Initialize client
    client = ExchangeRateClient(base_currency='BGN')
    
    try:
        # Get rates for EUR, USD, and GBP
        rates = client.get_rates(['EUR', 'USD', 'GBP'])
        
        print(f"\nExchange rates for 1 BGN:")
        for currency, rate in rates.items():
            print(f"  {currency}: {rate:.6f}")
            
    except Exception as e:
        print(f"Error: {e}")


def example_all_currencies():
    """Example 2: Fetch all available currencies."""
    print("\n" + "=" * 60)
    print("Example 2: Fetch All Currencies")
    print("=" * 60)
    
    client = ExchangeRateClient()
    
    try:
        # Get all available rates
        all_rates = client.get_rates()
        
        print(f"\nTotal currencies available: {len(all_rates)}")
        print("\nSample of available currencies:")
        
        # Show first 10 currencies
        for i, (currency, rate) in enumerate(list(all_rates.items())[:10]):
            print(f"  {currency}: {rate:.6f}")
        
        print("  ...")
        
    except Exception as e:
        print(f"Error: {e}")


def example_cache_behavior():
    """Example 3: Demonstrate caching behavior."""
    print("\n" + "=" * 60)
    print("Example 3: Cache Behavior")
    print("=" * 60)
    
    client = ExchangeRateClient()
    
    try:
        # First call - fetches from API
        print("\nFirst call (will fetch from API):")
        start_time = time.time()
        rates1 = client.get_rates(['EUR', 'USD'])
        elapsed1 = time.time() - start_time
        print(f"  EUR: {rates1['EUR']:.6f}")
        print(f"  USD: {rates1['USD']:.6f}")
        print(f"  Time taken: {elapsed1:.3f} seconds")
        
        # Second call - uses cache
        print("\nSecond call (will use cache):")
        start_time = time.time()
        rates2 = client.get_rates(['EUR', 'USD'])
        elapsed2 = time.time() - start_time
        print(f"  EUR: {rates2['EUR']:.6f}")
        print(f"  USD: {rates2['USD']:.6f}")
        print(f"  Time taken: {elapsed2:.3f} seconds")
        
        print(f"\nCache speedup: {elapsed1/elapsed2:.1f}x faster")
        
    except Exception as e:
        print(f"Error: {e}")


def example_error_handling():
    """Example 4: Error handling for invalid currencies."""
    print("\n" + "=" * 60)
    print("Example 4: Error Handling")
    print("=" * 60)
    
    client = ExchangeRateClient()
    
    # Try to fetch invalid currency
    print("\nAttempting to fetch invalid currency 'XYZ':")
    try:
        rates = client.get_rates(['XYZ'])
        print(f"Rates: {rates}")
    except ValueError as e:
        print(f"  Caught ValueError: {e}")
    except Exception as e:
        print(f"  Caught Exception: {e}")
    
    # Mix of valid and invalid currencies
    print("\nAttempting to fetch mix of valid and invalid currencies:")
    try:
        rates = client.get_rates(['EUR', 'XYZ', 'USD'])
        print(f"  Successfully fetched: {list(rates.keys())}")
        print(f"  Note: Invalid currency 'XYZ' was skipped")
    except Exception as e:
        print(f"  Error: {e}")


def example_cache_clearing():
    """Example 5: Clearing cache to force fresh API call."""
    print("\n" + "=" * 60)
    print("Example 5: Cache Clearing")
    print("=" * 60)
    
    client = ExchangeRateClient()
    
    try:
        # Fetch data (may use cache)
        print("\nFetching rates (may use cache):")
        rates1 = client.get_rates(['EUR'])
        print(f"  EUR: {rates1['EUR']:.6f}")
        
        # Clear cache
        print("\nClearing cache...")
        client.clear_cache()
        
        # Fetch again (will fetch from API)
        print("\nFetching rates again (will fetch from API):")
        rates2 = client.get_rates(['EUR'])
        print(f"  EUR: {rates2['EUR']:.6f}")
        
    except Exception as e:
        print(f"Error: {e}")


def example_conversion_calculation():
    """Example 6: Calculate currency conversions."""
    print("\n" + "=" * 60)
    print("Example 6: Currency Conversion Calculation")
    print("=" * 60)
    
    client = ExchangeRateClient(base_currency='BGN')
    
    try:
        # Get rates
        rates = client.get_rates(['EUR', 'USD', 'GBP'])
        
        # Amount in BGN to convert
        bgn_amount = 100
        
        print(f"\nConverting {bgn_amount} BGN to other currencies:")
        for currency, rate in rates.items():
            converted = bgn_amount * rate
            print(f"  {bgn_amount} BGN = {converted:.2f} {currency}")
        
        # Reverse conversion (from EUR to BGN)
        eur_amount = 50
        bgn_from_eur = eur_amount / rates['EUR']
        print(f"\nReverse conversion:")
        print(f"  {eur_amount} EUR = {bgn_from_eur:.2f} BGN")
        
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run all examples."""
    print("\n")
    print("*" * 60)
    print("Exchange Rate API Client - Usage Examples")
    print("*" * 60)
    
    # Run all examples
    example_basic_usage()
    example_all_currencies()
    example_cache_behavior()
    example_error_handling()
    example_cache_clearing()
    example_conversion_calculation()
    
    print("\n" + "*" * 60)
    print("All examples completed!")
    print("*" * 60 + "\n")


if __name__ == '__main__':
    main()
