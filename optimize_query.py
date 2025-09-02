#!/usr/bin/env python3
"""
Command-line interface for the Bankruptcy Query Optimizer.

Usage:
    python optimize_query.py "your query here"
    python optimize_query.py -f queries.txt
    python optimize_query.py -v 3 "section 363 sale"
"""

import argparse
import asyncio
import json
import sys
import os
from pathlib import Path
from bankruptcy_query_optimizer import BankruptcyQueryOptimizer


def print_version(version_name: str, version_data: dict, verbose: bool = False):
    """Print a single optimized version."""
    print(f"\n{version_name.upper()}: {version_data['query']}")
    
    if verbose and version_data['changes']:
        print(f"  Changes ({len(version_data['changes'])}):")
        for change in version_data['changes']:
            print(f"    - [{change['rule_id']}] {change['change']}")


async def optimize_single_query(optimizer: BankruptcyQueryOptimizer, query: str, 
                               version: int = None, verbose: bool = False, 
                               json_output: bool = False):
    """Optimize a single query and display results."""
    try:
        result = await optimizer.optimize_query(query)
        
        if json_output:
            # Output as JSON
            output = {
                "original_query": query,
                "optimized_queries": result['optimized_queries'],
                "execution_time": result['execution_time'],
                "active_consultants": result['active_consultant_names']
            }
            print(json.dumps(output, indent=2))
        else:
            # Human-readable output
            print(f"\nOriginal query: {query}")
            print(f"Execution time: {result['execution_time']}")
            print(f"Active consultants: {result['active_consultants']}/{result['consultant_count']}")
            
            queries = result['optimized_queries']
            
            if version:
                # Show specific version
                version_key = f"version{version}"
                if version_key in queries:
                    print_version(version_key, queries[version_key], verbose)
                else:
                    print(f"\nError: Version {version} not found")
            else:
                # Show all versions
                for v in ['version1', 'version2', 'version3', 'version4']:
                    if v in queries:
                        print_version(v, queries[v], verbose)
        
        return True
        
    except Exception as e:
        print(f"\nError optimizing query: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        return False


async def optimize_from_file(optimizer: BankruptcyQueryOptimizer, filename: str,
                           version: int = None, verbose: bool = False,
                           json_output: bool = False):
    """Optimize queries from a file (one per line)."""
    try:
        with open(filename, 'r') as f:
            queries = [line.strip() for line in f if line.strip()]
        
        print(f"\nProcessing {len(queries)} queries from {filename}...")
        
        results = []
        for i, query in enumerate(queries, 1):
            if not json_output:
                print(f"\n[{i}/{len(queries)}] ", end='')
            
            success = await optimize_single_query(optimizer, query, version, verbose, json_output)
            results.append(success)
        
        if not json_output:
            successful = sum(results)
            print(f"\n\nSummary: {successful}/{len(queries)} queries optimized successfully")
        
    except FileNotFoundError:
        print(f"\nError: File '{filename}' not found", file=sys.stderr)
    except Exception as e:
        print(f"\nError reading file: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='Optimize bankruptcy Boolean queries using AI consultants',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s "preference action"
  %(prog)s -v 3 "section 363 sale"
  %(prog)s -f queries.txt --json
  %(prog)s --verbose "Till v. SCS Credit"
        '''
    )
    
    # Query input options
    parser.add_argument('query', nargs='?', help='Query to optimize')
    parser.add_argument('-f', '--file', help='Read queries from file (one per line)')
    
    # Output options
    parser.add_argument('-v', '--version', type=int, choices=[1, 2, 3, 4],
                       help='Show only specific version (1-4)')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed change information')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON')
    
    # Model options
    parser.add_argument('--model', default='gpt-5',
                       help='Model to use (default: gpt-5)')
    parser.add_argument('--temperature', type=float, default=0.0,
                       help='Model temperature (ignored for gpt-5)')
    
    # Other options
    parser.add_argument('--no-logging', action='store_true',
                       help='Disable logging output')
    parser.add_argument('--consultants-dir', default='prompts/consultants',
                       help='Directory containing consultant prompts')
    parser.add_argument('--executive-path', default='prompts/executive/executive-agent.txt',
                       help='Path to executive agent prompt')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.query and not args.file:
        parser.error('Either provide a query or use -f to specify a file')
    
    if args.query and args.file:
        parser.error('Cannot specify both a query and a file')
    
    # Check for API key; fallback to loading from .env if missing
    if not os.getenv("OPENAI_API_KEY"):
        try:
            from dotenv import load_dotenv, find_dotenv
            # Load .env only as a fallback; do not override existing env
            load_dotenv(find_dotenv(), override=False)
        except Exception:
            # If python-dotenv isn't available, proceed to the next check
            pass
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set (you can add it to a .env file)", file=sys.stderr)
        sys.exit(1)
    
    # Initialize optimizer
    try:
        optimizer = BankruptcyQueryOptimizer(
            consultants_dir=args.consultants_dir,
            executive_path=args.executive_path,
            model=args.model,
            temperature=args.temperature,
            enable_logging=not args.no_logging and not args.json
        )
        
        if not args.json and not args.no_logging:
            summary = optimizer.get_agent_summary()
            print(f"Loaded {summary['consultant_count']} consultants using {summary['model']}")
        
    except Exception as e:
        print(f"Error initializing optimizer: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Run optimization
    if args.query:
        asyncio.run(optimize_single_query(
            optimizer, args.query, args.version, args.verbose, args.json
        ))
    else:
        asyncio.run(optimize_from_file(
            optimizer, args.file, args.version, args.verbose, args.json
        ))


if __name__ == '__main__':
    main()
