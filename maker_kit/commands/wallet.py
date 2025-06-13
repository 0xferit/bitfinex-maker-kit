"""
Wallet command - Show wallet balances.
"""

from ..utilities.auth import create_client


def wallet_command():
    """Get and display wallet balances"""
    client = create_client()
    
    try:
        wallets = client.get_wallets()
        
        print(f"\n💰 Wallet Balances:")
        print("─" * 60)
        print(f"{'Type':<15} {'Currency':<10} {'Balance':<15} {'Available':<15}")
        print("─" * 60)
        
        for wallet in wallets:
            wallet_type = wallet.wallet_type
            currency = wallet.currency
            balance = float(wallet.balance)
            available = float(wallet.available_balance)
            
            # Only show non-zero balances
            if balance != 0 or available != 0:
                print(f"{wallet_type:<15} {currency:<10} {balance:<15.6f} {available:<15.6f}")
        
        print("─" * 60)
        return wallets
    except Exception as e:
        print(f"❌ Failed to get wallet data: {e}")
        return [] 