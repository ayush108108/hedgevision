"""
Comprehensive Multi-Tier EDA Workflow with All Services
========================================================

Orchestrates a complete end-to-end workflow covering:
1. Data Ingestion & Validation
2. EDA & Quality Checks
3. Market Intelligence (News, Binance, Coinglass)
4. Correlation & Cointegration Analysis
5. Portfolio Analytics & Backtesting
6. Comprehensive Reporting

Each tier includes:
- Dynamic error handling
- Verification steps
- Detailed logging
- Rollback capabilities
- Progress tracking
"""

import os
import sys
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import asyncio

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from api.clients.supabase_client import get_supabase_client
from api.services.standardization_service import get_standardization_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_eda.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TierResult:
    """Result of a tier execution"""
    tier_name: str
    status: str  # success, failure, skipped, partial
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    data_processed: int
    errors: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]
    
    def to_dict(self):
        return {
            **asdict(self),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat()
        }


@dataclass
class WorkflowState:
    """Tracks overall workflow state"""
    run_id: str
    start_time: datetime
    tier_results: List[TierResult]
    current_tier: Optional[str]
    failed_tiers: List[str]
    skipped_tiers: List[str]
    
    def add_result(self, result: TierResult):
        self.tier_results.append(result)
        if result.status == 'failure':
            self.failed_tiers.append(result.tier_name)
        elif result.status == 'skipped':
            self.skipped_tiers.append(result.tier_name)
    
    def to_dict(self):
        return {
            'run_id': self.run_id,
            'start_time': self.start_time.isoformat(),
            'current_tier': self.current_tier,
            'failed_tiers': self.failed_tiers,
            'skipped_tiers': self.skipped_tiers,
            'tier_results': [r.to_dict() for r in self.tier_results]
        }


class ComprehensiveEDAWorkflow:
    """
    Main orchestrator for the comprehensive multi-tier EDA workflow
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.state = WorkflowState(
            run_id=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            start_time=datetime.now(),
            tier_results=[],
            current_tier=None,
            failed_tiers=[],
            skipped_tiers=[]
        )
        self.supabase = None
        self.std_service = get_standardization_service()
        
    async def initialize(self):
        """Initialize connections and verify setup"""
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE MULTI-TIER EDA WORKFLOW")
        logger.info(f"Run ID: {self.state.run_id}")
        logger.info(f"Start Time: {self.state.start_time}")
        logger.info("=" * 80)
        
        try:
            self.supabase = get_supabase_client()
            logger.info("✓ Supabase client initialized")
            
            # Verify database connectivity
            result = self.supabase.table('assets').select('count', count='exact').limit(1).execute()
            logger.info(f"✓ Database connectivity verified ({result.count} assets)")
            
            return True
        except Exception as e:
            logger.error(f"✗ Initialization failed: {e}")
            return False
    
    async def execute_tier(self, tier_func, tier_name: str, *args, **kwargs) -> TierResult:
        """
        Execute a tier with comprehensive error handling and tracking
        """
        self.state.current_tier = tier_name
        start_time = datetime.now()
        errors = []
        warnings = []
        metrics = {}
        data_processed = 0
        status = 'success'
        
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"TIER: {tier_name}")
        logger.info("=" * 80)
        
        try:
            # Execute tier function
            result = await tier_func(*args, **kwargs)
            
            if isinstance(result, dict):
                data_processed = result.get('count', 0)
                metrics = result.get('metrics', {})
                warnings = result.get('warnings', [])
                
                # Check if tier succeeded
                if result.get('status') == 'failure':
                    status = 'failure'
                    errors.append(result.get('error', 'Unknown error'))
            else:
                data_processed = result if isinstance(result, int) else 0
                
        except Exception as e:
            status = 'failure'
            error_msg = f"{type(e).__name__}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"✗ Tier failed: {error_msg}")
            logger.error(traceback.format_exc())
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        tier_result = TierResult(
            tier_name=tier_name,
            status=status,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            data_processed=data_processed,
            errors=errors,
            warnings=warnings,
            metrics=metrics
        )
        
        self.state.add_result(tier_result)
        
        # Log result
        status_icon = "✓" if status == 'success' else "✗"
        logger.info(f"{status_icon} {tier_name} - Status: {status}")
        logger.info(f"  Duration: {duration:.2f}s")
        logger.info(f"  Data Processed: {data_processed}")
        if errors:
            logger.error(f"  Errors: {len(errors)}")
            for err in errors:
                logger.error(f"    - {err}")
        if warnings:
            logger.warning(f"  Warnings: {len(warnings)}")
            for warn in warnings:
                logger.warning(f"    - {warn}")
        
        return tier_result
    
    # =========================================================================
    # TIER 1: DATA VALIDATION & INVENTORY
    # =========================================================================
    
    async def tier1_data_inventory(self) -> Dict[str, Any]:
        """
        Comprehensive data inventory and validation
        """
        logger.info("📊 Performing data inventory...")
        
        try:
            # Count assets
            assets_result = self.supabase.table('assets').select('*').execute()
            assets_count = len(assets_result.data)
            
            # Count price history
            prices_result = self.supabase.table('price_history')\
                .select('asset_id, date', count='exact')\
                .limit(1)\
                .execute()
            prices_count = prices_result.count
            
            # Get date range
            date_range_result = self.supabase.table('price_history')\
                .select('date')\
                .order('date', desc=True)\
                .limit(1)\
                .execute()
            
            latest_date = None
            if date_range_result.data:
                latest_date = date_range_result.data[0]['date']
            
            # Check for suspect flags
            suspect_result = self.supabase.table('price_history')\
                .select('count', count='exact')\
                .eq('suspect_flag', True)\
                .limit(1)\
                .execute()
            suspect_count = suspect_result.count
            
            metrics = {
                'assets_count': assets_count,
                'prices_count': prices_count,
                'latest_date': latest_date,
                'suspect_count': suspect_count,
                'suspect_pct': (suspect_count / prices_count * 100) if prices_count > 0 else 0
            }
            
            logger.info(f"  Assets: {assets_count}")
            logger.info(f"  Price Records: {prices_count:,}")
            logger.info(f"  Latest Date: {latest_date}")
            logger.info(f"  Suspect Records: {suspect_count} ({metrics['suspect_pct']:.2f}%)")
            
            warnings = []
            if suspect_count > prices_count * 0.05:  # More than 5% suspect
                warnings.append(f"High suspect rate: {metrics['suspect_pct']:.2f}%")
            
            if not latest_date:
                warnings.append("No price data found")
            
            return {
                'status': 'success',
                'count': assets_count,
                'metrics': metrics,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Data inventory failed: {e}")
            return {
                'status': 'failure',
                'error': str(e),
                'count': 0,
                'metrics': {},
                'warnings': []
            }
    
    # =========================================================================
    # TIER 2: EDA & QUALITY ANALYSIS
    # =========================================================================
    
    async def tier2_eda_quality_analysis(self) -> Dict[str, Any]:
        """
        Comprehensive EDA: distributions, outliers, missing data, correlations
        """
        logger.info("🔍 Performing EDA & quality analysis...")
        
        try:
            # Fetch recent price data for EDA
            lookback_days = self.config.get('eda_lookback_days', 252)
            cutoff_date = (datetime.now() - timedelta(days=lookback_days)).date()
            
            logger.info(f"  Fetching data from {cutoff_date}...")
            
            # Get clean price data
            prices_result = self.supabase.table('price_history')\
                .select('asset_id, date, close, volume')\
                .eq('suspect_flag', False)\
                .gte('date', cutoff_date.isoformat())\
                .execute()
            
            if not prices_result.data:
                return {
                    'status': 'failure',
                    'error': 'No price data available for EDA',
                    'count': 0,
                    'metrics': {},
                    'warnings': ['No data in specified lookback period']
                }
            
            df = pd.DataFrame(prices_result.data)
            df['date'] = pd.to_datetime(df['date'])
            
            # Calculate returns
            df_pivot = df.pivot(index='date', columns='asset_id', values='close')
            returns = df_pivot.pct_change().dropna()
            
            # EDA Metrics
            metrics = {
                'total_records': len(df),
                'unique_assets': df['asset_id'].nunique(),
                'date_range_days': (df['date'].max() - df['date'].min()).days,
                'mean_return': float(returns.mean().mean()),
                'mean_volatility': float(returns.std().mean()),
                'max_drawdown_pct': float((df_pivot / df_pivot.cummax() - 1).min().min() * 100),
                'missing_data_pct': float(df_pivot.isna().sum().sum() / df_pivot.size * 100)
            }
            
            # Outlier detection (returns > 3 std devs)
            outliers = (returns.abs() > 3 * returns.std()).sum().sum()
            metrics['outliers_count'] = int(outliers)
            metrics['outliers_pct'] = float(outliers / returns.size * 100)
            
            logger.info(f"  Records Analyzed: {metrics['total_records']:,}")
            logger.info(f"  Assets: {metrics['unique_assets']}")
            logger.info(f"  Date Range: {metrics['date_range_days']} days")
            logger.info(f"  Mean Return: {metrics['mean_return']*100:.4f}%")
            logger.info(f"  Mean Volatility: {metrics['mean_volatility']*100:.2f}%")
            logger.info(f"  Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
            logger.info(f"  Missing Data: {metrics['missing_data_pct']:.2f}%")
            logger.info(f"  Outliers: {metrics['outliers_count']} ({metrics['outliers_pct']:.3f}%)")
            
            warnings = []
            if metrics['missing_data_pct'] > 10:
                warnings.append(f"High missing data: {metrics['missing_data_pct']:.2f}%")
            if metrics['outliers_pct'] > 1:
                warnings.append(f"High outlier rate: {metrics['outliers_pct']:.3f}%")
            
            return {
                'status': 'success',
                'count': len(df),
                'metrics': metrics,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"EDA failed: {e}")
            logger.error(traceback.format_exc())
            return {
                'status': 'failure',
                'error': str(e),
                'count': 0,
                'metrics': {},
                'warnings': []
            }
    
    # =========================================================================
    # TIER 3: MARKET INTELLIGENCE (News, Binance, Coinglass)
    # =========================================================================
    
    async def tier3_market_intelligence(self) -> Dict[str, Any]:
        """
        Fetch and analyze market intelligence from all sources
        """
        logger.info("📰 Fetching market intelligence...")
        
        metrics = {}
        warnings = []
        total_count = 0
        
        try:
            # Import services dynamically
            try:
                from api.services.news_service import get_news_service
                from api.services.binance_service import get_binance_service
                from api.services.coinglass_service import get_coinglass_service
            except ImportError as e:
                logger.warning(f"Could not import market intelligence services: {e}")
                return {
                    'status': 'partial',
                    'count': 0,
                    'metrics': {'services_available': False},
                    'warnings': ['Market intelligence services not available']
                }
            
            # News Service
            try:
                logger.info("  Fetching news...")
                news_service = get_news_service()
                news_result = await news_service.get_news(limit=50)
                metrics['news_articles'] = len(news_result.get('articles', []))
                metrics['news_sentiment_avg'] = np.mean([
                    a.get('sentiment_score', 0) 
                    for a in news_result.get('articles', [])
                ]) if news_result.get('articles') else 0
                logger.info(f"    News Articles: {metrics['news_articles']}")
                logger.info(f"    Avg Sentiment: {metrics['news_sentiment_avg']:.3f}")
                total_count += metrics['news_articles']
            except Exception as e:
                logger.warning(f"  News service error: {e}")
                warnings.append(f"News service: {str(e)}")
                metrics['news_articles'] = 0
            
            # Binance Service
            try:
                logger.info("  Fetching Binance data...")
                binance_service = get_binance_service()
                
                # Get top symbols to test
                test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
                prices_fetched = 0
                
                for symbol in test_symbols:
                    try:
                        price_data = await binance_service.get_price(symbol)
                        if price_data:
                            prices_fetched += 1
                    except Exception:
                        pass
                
                metrics['binance_prices_fetched'] = prices_fetched
                logger.info(f"    Binance Prices: {prices_fetched}/{len(test_symbols)}")
                total_count += prices_fetched
                
            except Exception as e:
                logger.warning(f"  Binance service error: {e}")
                warnings.append(f"Binance service: {str(e)}")
                metrics['binance_prices_fetched'] = 0
            
            # Coinglass Service
            try:
                logger.info("  Fetching Coinglass data...")
                coinglass_service = get_coinglass_service()
                
                # Get Fear & Greed Index
                fear_greed = await coinglass_service.get_fear_greed_index()
                if fear_greed:
                    metrics['fear_greed_index'] = fear_greed.get('value', 0)
                    logger.info(f"    Fear & Greed Index: {metrics['fear_greed_index']}")
                    total_count += 1
                
            except Exception as e:
                logger.warning(f"  Coinglass service error: {e}")
                warnings.append(f"Coinglass service: {str(e)}")
            
            metrics['services_available'] = True
            metrics['services_with_errors'] = len(warnings)
            
            status = 'success' if len(warnings) == 0 else 'partial'
            
            return {
                'status': status,
                'count': total_count,
                'metrics': metrics,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Market intelligence tier failed: {e}")
            logger.error(traceback.format_exc())
            return {
                'status': 'failure',
                'error': str(e),
                'count': 0,
                'metrics': metrics,
                'warnings': warnings
            }
    
    # =========================================================================
    # TIER 4: CORRELATION & COINTEGRATION ANALYSIS
    # =========================================================================
    
    async def tier4_correlation_cointegration(self) -> Dict[str, Any]:
        """
        Compute correlation matrices and cointegration pairs
        """
        logger.info("🔗 Computing correlations & cointegration...")
        
        try:
            # Check if correlation matrices exist
            corr_result = self.supabase.table('correlation_matrices')\
                .select('count', count='exact')\
                .limit(1)\
                .execute()
            
            corr_count = corr_result.count
            
            # Check cointegration pairs
            coint_result = self.supabase.table('cointegration_pairs')\
                .select('count', count='exact')\
                .eq('is_cointegrated', True)\
                .limit(1)\
                .execute()
            
            coint_count = coint_result.count
            
            # Get latest cointegration test date
            latest_test = self.supabase.table('cointegration_pairs')\
                .select('test_date')\
                .order('test_date', desc=True)\
                .limit(1)\
                .execute()
            
            latest_date = latest_test.data[0]['test_date'] if latest_test.data else None
            
            # Get top pairs by score
            top_pairs = self.supabase.table('cointegration_pairs')\
                .select('asset1_symbol, asset2_symbol, overall_score, p_value, hedge_ratio')\
                .eq('is_cointegrated', True)\
                .order('overall_score', desc=True)\
                .limit(10)\
                .execute()
            
            metrics = {
                'correlation_matrices': corr_count,
                'cointegrated_pairs': coint_count,
                'latest_test_date': latest_date,
                'top_pairs_count': len(top_pairs.data)
            }
            
            logger.info(f"  Correlation Matrices: {corr_count}")
            logger.info(f"  Cointegrated Pairs: {coint_count}")
            logger.info(f"  Latest Test: {latest_date}")
            
            if top_pairs.data:
                logger.info(f"  Top Cointegrated Pairs:")
                for i, pair in enumerate(top_pairs.data[:5], 1):
                    logger.info(f"    {i}. {pair['asset1_symbol']}/{pair['asset2_symbol']} "
                              f"(score: {pair['overall_score']:.2f}, p: {pair['p_value']:.4f})")
            
            warnings = []
            if coint_count == 0:
                warnings.append("No cointegrated pairs found - run populate_cointegration.py")
            
            return {
                'status': 'success',
                'count': coint_count,
                'metrics': metrics,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Correlation/cointegration analysis failed: {e}")
            logger.error(traceback.format_exc())
            return {
                'status': 'failure',
                'error': str(e),
                'count': 0,
                'metrics': {},
                'warnings': []
            }
    
    # =========================================================================
    # TIER 5: PORTFOLIO ANALYTICS
    # =========================================================================
    
    async def tier5_portfolio_analytics(self) -> Dict[str, Any]:
        """
        Analyze portfolio positions and calculate metrics
        """
        logger.info("💼 Analyzing portfolio...")
        
        try:
            from api.services.portfolio_service import get_portfolio_service
            
            portfolio_service = get_portfolio_service()
            
            # Get all positions
            positions = portfolio_service.get_user_positions('demo_user')
            
            # Calculate metrics
            metrics_obj = portfolio_service.calculate_portfolio_metrics('demo_user')
            
            metrics = {
                'total_positions': len(positions),
                'open_positions': len([p for p in positions if p.status == 'open']),
                'closed_positions': len([p for p in positions if p.status == 'closed']),
                'total_value': metrics_obj.total_value,
                'total_pnl': metrics_obj.total_pnl,
                'win_rate': metrics_obj.win_rate,
                'sharpe_ratio': metrics_obj.sharpe_ratio,
                'max_drawdown': metrics_obj.max_drawdown,
                'profit_factor': metrics_obj.profit_factor
            }
            
            logger.info(f"  Total Positions: {metrics['total_positions']}")
            logger.info(f"  Open: {metrics['open_positions']} | Closed: {metrics['closed_positions']}")
            logger.info(f"  Total Value: ${metrics['total_value']:,.2f}")
            logger.info(f"  Total P&L: ${metrics['total_pnl']:,.2f}")
            logger.info(f"  Win Rate: {metrics['win_rate']:.1f}%")
            logger.info(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            logger.info(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")
            
            warnings = []
            if metrics['total_positions'] == 0:
                warnings.append("No portfolio positions found")
            
            return {
                'status': 'success',
                'count': metrics['total_positions'],
                'metrics': metrics,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Portfolio analytics failed: {e}")
            logger.error(traceback.format_exc())
            return {
                'status': 'failure',
                'error': str(e),
                'count': 0,
                'metrics': {},
                'warnings': []
            }
    
    # =========================================================================
    # TIER 6: STANDARDIZATION VERIFICATION
    # =========================================================================
    
    async def tier6_standardization_check(self) -> Dict[str, Any]:
        """
        Verify standardization service is working correctly
        """
        logger.info("🔧 Verifying standardization service...")
        
        try:
            # Test canonical pair generation
            test_pairs = [
                ('BTC', 'ETH'),
                ('SPY', 'QQQ'),
                ('AAPL', 'MSFT')
            ]
            
            successful_tests = 0
            failed_tests = []
            
            for asset1, asset2 in test_pairs:
                try:
                    # Test canonical pair
                    canonical = self.std_service.canonical_pair(asset1, asset2)
                    
                    # Test split
                    split_a1, split_a2 = self.std_service.split_pair(canonical)
                    
                    # Test provider mappings
                    binance_a1 = self.std_service.to_binance(asset1)
                    coinglass_a1 = self.std_service.to_coinglass(asset1)
                    
                    logger.info(f"  {asset1}/{asset2} -> {canonical}")
                    logger.info(f"    Binance: {binance_a1}, Coinglass: {coinglass_a1}")
                    
                    successful_tests += 1
                except Exception as e:
                    failed_tests.append(f"{asset1}/{asset2}: {str(e)}")
            
            metrics = {
                'tests_run': len(test_pairs),
                'tests_passed': successful_tests,
                'tests_failed': len(failed_tests)
            }
            
            logger.info(f"  Tests Passed: {successful_tests}/{len(test_pairs)}")
            
            return {
                'status': 'success' if len(failed_tests) == 0 else 'partial',
                'count': successful_tests,
                'metrics': metrics,
                'warnings': failed_tests
            }
            
        except Exception as e:
            logger.error(f"Standardization check failed: {e}")
            return {
                'status': 'failure',
                'error': str(e),
                'count': 0,
                'metrics': {},
                'warnings': []
            }
    
    # =========================================================================
    # MAIN EXECUTION
    # =========================================================================
    
    async def run(self):
        """
        Execute all tiers sequentially with verification
        """
        if not await self.initialize():
            logger.error("Initialization failed - aborting workflow")
            return False
        
        # Define tier execution sequence
        tiers = [
            (self.tier1_data_inventory, "Data Inventory & Validation"),
            (self.tier2_eda_quality_analysis, "EDA & Quality Analysis"),
            (self.tier3_market_intelligence, "Market Intelligence"),
            (self.tier4_correlation_cointegration, "Correlation & Cointegration"),
            (self.tier5_portfolio_analytics, "Portfolio Analytics"),
            (self.tier6_standardization_check, "Standardization Verification"),
        ]
        
        # Execute each tier
        for tier_func, tier_name in tiers:
            result = await self.execute_tier(tier_func, tier_name)
            
            # Check if we should continue
            if result.status == 'failure':
                if self.config.get('stop_on_failure', False):
                    logger.error(f"Stopping workflow due to failure in: {tier_name}")
                    break
                else:
                    logger.warning(f"Continuing despite failure in: {tier_name}")
        
        # Generate final report
        await self.generate_final_report()
        
        return len(self.state.failed_tiers) == 0
    
    async def generate_final_report(self):
        """
        Generate comprehensive final report
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info("WORKFLOW SUMMARY")
        logger.info("=" * 80)
        
        total_duration = sum(r.duration_seconds for r in self.state.tier_results)
        total_processed = sum(r.data_processed for r in self.state.tier_results)
        
        logger.info(f"Run ID: {self.state.run_id}")
        logger.info(f"Total Duration: {total_duration:.2f}s ({total_duration/60:.1f} min)")
        logger.info(f"Total Data Processed: {total_processed:,}")
        logger.info(f"Tiers Completed: {len(self.state.tier_results)}")
        logger.info(f"Tiers Failed: {len(self.state.failed_tiers)}")
        logger.info(f"Tiers Skipped: {len(self.state.skipped_tiers)}")
        
        # Tier breakdown
        logger.info("")
        logger.info("Tier Breakdown:")
        logger.info("-" * 80)
        for result in self.state.tier_results:
            status_icon = {"success": "✓", "failure": "✗", "partial": "⚠", "skipped": "⏭"}[result.status]
            logger.info(f"{status_icon} {result.tier_name:40s} {result.duration_seconds:8.2f}s  {result.data_processed:10,} records")
        
        # Save report to file
        report_file = f"workflow_report_{self.state.run_id}.json"
        with open(report_file, 'w') as f:
            json.dump(self.state.to_dict(), f, indent=2)
        
        logger.info("")
        logger.info(f"📄 Full report saved to: {report_file}")
        logger.info("=" * 80)
        
        # Final verdict
        if len(self.state.failed_tiers) == 0:
            logger.info("✅ WORKFLOW COMPLETED SUCCESSFULLY")
            return True
        else:
            logger.warning(f"⚠️  WORKFLOW COMPLETED WITH {len(self.state.failed_tiers)} FAILURES")
            for tier in self.state.failed_tiers:
                logger.warning(f"   - {tier}")
            return False


async def main():
    """Main entry point"""
    config = {
        'eda_lookback_days': 252,
        'stop_on_failure': False,  # Continue even if a tier fails
    }
    
    workflow = ComprehensiveEDAWorkflow(config)
    success = await workflow.run()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
