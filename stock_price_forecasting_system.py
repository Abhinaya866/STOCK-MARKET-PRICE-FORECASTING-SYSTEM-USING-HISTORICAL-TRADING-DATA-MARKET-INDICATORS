"""
Stock Market Price Forecasting System using Time-Series Analysis and ML
Forecasts future stock prices using historical trading data and market indicators
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def generate_stock_data(n_days=500, random_state=42):
    """Generate synthetic stock market data"""
    np.random.seed(random_state)
    
    dates = pd.date_range(start='2022-01-01', periods=n_days, freq='D')
    
    # Generate realistic stock prices with trend and volatility
    price = 100
    prices = [price]
    volumes = [np.random.lognormal(mean=15, sigma=0.5)]
    
    for i in range(1, n_days):
        # Random walk with drift
        change = np.random.normal(0.001, 0.02)
        price = price * (1 + change)
        prices.append(price)
        
        # Volume (inversely correlated with volatility)
        volume = np.random.lognormal(mean=15, sigma=0.5)
        volumes.append(volume)
    
    df = pd.DataFrame({
        'Date': dates,
        'Open': np.array(prices) * (1 + np.random.normal(0, 0.005, n_days)),
        'High': np.array(prices) * (1 + np.abs(np.random.normal(0, 0.01, n_days))),
        'Low': np.array(prices) * (1 - np.abs(np.random.normal(0, 0.01, n_days))),
        'Close': prices,
        'Volume': volumes
    })
    
    # Ensure High >= Close >= Low >= Open
    df['High'] = df[['Open', 'High', 'Close']].max(axis=1) * 1.01
    df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1) * 0.99
    
    df.to_csv('/home/ubuntu/stock_market_data.csv', index=False)
    print(f"Generated stock market dataset: {len(df)} days")
    return df

def calculate_technical_indicators(df):
    """Calculate technical indicators"""
    df_indicators = df.copy()
    
    # Simple Moving Averages
    df_indicators['SMA_10'] = df_indicators['Close'].rolling(window=10).mean()
    df_indicators['SMA_20'] = df_indicators['Close'].rolling(window=20).mean()
    df_indicators['SMA_50'] = df_indicators['Close'].rolling(window=50).mean()
    
    # Exponential Moving Average
    df_indicators['EMA_12'] = df_indicators['Close'].ewm(span=12).mean()
    df_indicators['EMA_26'] = df_indicators['Close'].ewm(span=26).mean()
    
    # MACD
    df_indicators['MACD'] = df_indicators['EMA_12'] - df_indicators['EMA_26']
    df_indicators['Signal_Line'] = df_indicators['MACD'].ewm(span=9).mean()
    
    # RSI (Relative Strength Index)
    delta = df_indicators['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df_indicators['RSI'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    df_indicators['BB_Middle'] = df_indicators['Close'].rolling(window=20).mean()
    bb_std = df_indicators['Close'].rolling(window=20).std()
    df_indicators['BB_Upper'] = df_indicators['BB_Middle'] + (bb_std * 2)
    df_indicators['BB_Lower'] = df_indicators['BB_Middle'] - (bb_std * 2)
    
    # Volume indicators
    df_indicators['Volume_SMA'] = df_indicators['Volume'].rolling(window=20).mean()
    df_indicators['Price_Volume_Trend'] = (df_indicators['Close'].pct_change() * df_indicators['Volume']).rolling(window=20).mean()
    
    # Daily returns
    df_indicators['Daily_Return'] = df_indicators['Close'].pct_change()
    df_indicators['Volatility'] = df_indicators['Daily_Return'].rolling(window=20).std()
    
    return df_indicators

def prepare_features_for_forecasting(df_indicators, lookback=30):
    """Prepare features for forecasting models"""
    df_clean = df_indicators.dropna()
    
    features = ['Close', 'Volume', 'SMA_10', 'SMA_20', 'SMA_50', 'EMA_12', 'EMA_26',
                'MACD', 'RSI', 'BB_Upper', 'BB_Lower', 'Volatility']
    
    X = []
    y = []
    
    for i in range(len(df_clean) - lookback):
        X.append(df_clean[features].iloc[i:i+lookback].values.flatten())
        y.append(df_clean['Close'].iloc[i+lookback])
    
    X = np.array(X)
    y = np.array(y)
    
    # Normalize features
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X.reshape(-1, X.shape[-1])).reshape(X.shape)
    
    # Train-test split
    split_idx = int(0.8 * len(X))
    X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    return X_train, X_test, y_train, y_test, scaler, df_clean

def train_forecasting_models(X_train, X_test, y_train, y_test):
    """Train multiple forecasting models"""
    results = []
    predictions = {}
    
    # Linear Regression
    lr_model = LinearRegression()
    lr_model.fit(X_train, y_train)
    y_pred_lr = lr_model.predict(X_test)
    
    mse_lr = mean_squared_error(y_test, y_pred_lr)
    mae_lr = mean_absolute_error(y_test, y_pred_lr)
    rmse_lr = np.sqrt(mse_lr)
    r2_lr = r2_score(y_test, y_pred_lr)
    mape_lr = np.mean(np.abs((y_test - y_pred_lr) / y_test)) * 100
    
    results.append({
        'Model': 'Linear Regression',
        'RMSE': round(rmse_lr, 4),
        'MAE': round(mae_lr, 4),
        'R2_Score': round(r2_lr, 4),
        'MAPE': round(mape_lr, 4)
    })
    predictions['Linear Regression'] = y_pred_lr
    
    # Random Forest
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf_model.fit(X_train, y_train)
    y_pred_rf = rf_model.predict(X_test)
    
    mse_rf = mean_squared_error(y_test, y_pred_rf)
    mae_rf = mean_absolute_error(y_test, y_pred_rf)
    rmse_rf = np.sqrt(mse_rf)
    r2_rf = r2_score(y_test, y_pred_rf)
    mape_rf = np.mean(np.abs((y_test - y_pred_rf) / y_test)) * 100
    
    results.append({
        'Model': 'Random Forest',
        'RMSE': round(rmse_rf, 4),
        'MAE': round(mae_rf, 4),
        'R2_Score': round(r2_rf, 4),
        'MAPE': round(mape_rf, 4)
    })
    predictions['Random Forest'] = y_pred_rf
    
    # Gradient Boosting
    gb_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
    gb_model.fit(X_train, y_train)
    y_pred_gb = gb_model.predict(X_test)
    
    mse_gb = mean_squared_error(y_test, y_pred_gb)
    mae_gb = mean_absolute_error(y_test, y_pred_gb)
    rmse_gb = np.sqrt(mse_gb)
    r2_gb = r2_score(y_test, y_pred_gb)
    mape_gb = np.mean(np.abs((y_test - y_pred_gb) / y_test)) * 100
    
    results.append({
        'Model': 'Gradient Boosting',
        'RMSE': round(rmse_gb, 4),
        'MAE': round(mae_gb, 4),
        'R2_Score': round(r2_gb, 4),
        'MAPE': round(mape_gb, 4)
    })
    predictions['Gradient Boosting'] = y_pred_gb
    
    results_df = pd.DataFrame(results)
    results_df.to_csv('/home/ubuntu/forecasting_model_results.csv', index=False)
    
    return results_df, predictions, y_test, gb_model

def generate_visualizations(df, df_indicators, results_df, predictions, y_test, gb_model):
    """Generate comprehensive visualizations"""
    
    # 1. Stock Price Trends with Technical Indicators
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    axes[0].plot(df['Date'][-200:], df['Close'][-200:], label='Close Price', linewidth=2, color='#1f77b4')
    axes[0].plot(df_indicators['Date'][-200:], df_indicators['SMA_20'][-200:], label='SMA 20', linewidth=1.5, alpha=0.7)
    axes[0].plot(df_indicators['Date'][-200:], df_indicators['SMA_50'][-200:], label='SMA 50', linewidth=1.5, alpha=0.7)
    axes[0].set_ylabel('Price ($)', fontsize=11, fontweight='bold')
    axes[0].set_title('Stock Price with Moving Averages', fontsize=12, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(df_indicators['Date'][-200:], df_indicators['RSI'][-200:], label='RSI', linewidth=2, color='#ff7f0e')
    axes[1].axhline(y=70, color='r', linestyle='--', alpha=0.5, label='Overbought (70)')
    axes[1].axhline(y=30, color='g', linestyle='--', alpha=0.5, label='Oversold (30)')
    axes[1].set_ylabel('RSI', fontsize=11, fontweight='bold')
    axes[1].set_title('Relative Strength Index (RSI)', fontsize=12, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim([0, 100])
    
    axes[2].plot(df_indicators['Date'][-200:], df_indicators['MACD'][-200:], label='MACD', linewidth=2, color='#2ca02c')
    axes[2].plot(df_indicators['Date'][-200:], df_indicators['Signal_Line'][-200:], label='Signal Line', linewidth=1.5, alpha=0.7)
    axes[2].fill_between(df_indicators['Date'][-200:], df_indicators['MACD'][-200:], df_indicators['Signal_Line'][-200:], alpha=0.3)
    axes[2].set_xlabel('Date', fontsize=11, fontweight='bold')
    axes[2].set_ylabel('MACD', fontsize=11, fontweight='bold')
    axes[2].set_title('MACD and Signal Line', fontsize=12, fontweight='bold')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/home/ubuntu/stock_technical_indicators.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: stock_technical_indicators.png")
    
    # 2. Model Performance Comparison
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    models = results_df['Model'].tolist()
    rmse_values = results_df['RMSE'].tolist()
    mae_values = results_df['MAE'].tolist()
    r2_values = results_df['R2_Score'].tolist()
    mape_values = results_df['MAPE'].tolist()
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
    
    axes[0, 0].bar(models, rmse_values, color=colors)
    axes[0, 0].set_ylabel('RMSE', fontsize=11, fontweight='bold')
    axes[0, 0].set_title('Model Comparison: RMSE (Lower is Better)', fontsize=12, fontweight='bold')
    axes[0, 0].grid(True, alpha=0.3, axis='y')
    
    axes[0, 1].bar(models, mae_values, color=colors)
    axes[0, 1].set_ylabel('MAE', fontsize=11, fontweight='bold')
    axes[0, 1].set_title('Model Comparison: MAE (Lower is Better)', fontsize=12, fontweight='bold')
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    
    axes[1, 0].bar(models, r2_values, color=colors)
    axes[1, 0].set_ylabel('R² Score', fontsize=11, fontweight='bold')
    axes[1, 0].set_title('Model Comparison: R² Score (Higher is Better)', fontsize=12, fontweight='bold')
    axes[1, 0].grid(True, alpha=0.3, axis='y')
    
    axes[1, 1].bar(models, mape_values, color=colors)
    axes[1, 1].set_ylabel('MAPE (%)', fontsize=11, fontweight='bold')
    axes[1, 1].set_title('Model Comparison: MAPE (Lower is Better)', fontsize=12, fontweight='bold')
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('/home/ubuntu/stock_model_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: stock_model_comparison.png")
    
    # 3. Predictions vs Actual
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    for idx, (model_name, y_pred) in enumerate(predictions.items()):
        row = idx // 2
        col = idx % 2
        
        axes[row, col].plot(y_test[-100:], label='Actual', linewidth=2, marker='o', markersize=4)
        axes[row, col].plot(y_pred[-100:], label='Predicted', linewidth=2, marker='s', markersize=4, alpha=0.7)
        axes[row, col].set_title(f'{model_name}: Predictions vs Actual', fontsize=12, fontweight='bold')
        axes[row, col].set_xlabel('Test Sample', fontsize=11, fontweight='bold')
        axes[row, col].set_ylabel('Price ($)', fontsize=11, fontweight='bold')
        axes[row, col].legend()
        axes[row, col].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/home/ubuntu/stock_predictions_vs_actual.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: stock_predictions_vs_actual.png")
    
    # 4. Volume and Volatility Analysis
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))
    
    axes[0].bar(df['Date'][-200:], df['Volume'][-200:], color='#4ECDC4', alpha=0.7)
    axes[0].set_ylabel('Volume', fontsize=11, fontweight='bold')
    axes[0].set_title('Trading Volume Over Time', fontsize=12, fontweight='bold')
    axes[0].grid(True, alpha=0.3, axis='y')
    
    axes[1].plot(df_indicators['Date'][-200:], df_indicators['Volatility'][-200:], linewidth=2, color='#FF6B6B')
    axes[1].fill_between(df_indicators['Date'][-200:], df_indicators['Volatility'][-200:], alpha=0.3, color='#FF6B6B')
    axes[1].set_xlabel('Date', fontsize=11, fontweight='bold')
    axes[1].set_ylabel('Volatility (20-day Std Dev)', fontsize=11, fontweight='bold')
    axes[1].set_title('Price Volatility Over Time', fontsize=12, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/home/ubuntu/stock_volume_volatility.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: stock_volume_volatility.png")
    
    # 5. Feature Importance (Gradient Boosting)
    feature_names = ['Close', 'Volume', 'SMA_10', 'SMA_20', 'SMA_50', 'EMA_12', 'EMA_26',
                     'MACD', 'RSI', 'BB_Upper', 'BB_Lower', 'Volatility']
    
    fig, ax = plt.subplots(figsize=(10, 6))
    importance = gb_model.feature_importances_
    # Get top features (limited to available features)
    n_top = min(10, len(importance))
    indices = np.argsort(importance)[-n_top:]
    
    ax.barh(range(len(indices)), importance[indices], color='#45B7D1')
    ax.set_yticks(range(len(indices)))
    # Map feature indices correctly
    feature_labels = []
    for idx in indices:
        if idx < len(feature_names):
            feature_labels.append(feature_names[idx])
        else:
            feature_labels.append(f'Feature_{idx}')
    ax.set_yticklabels(feature_labels)
    ax.set_xlabel('Importance', fontsize=11, fontweight='bold')
    ax.set_title('Top 10 Feature Importance (Gradient Boosting)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    plt.savefig('/home/ubuntu/stock_feature_importance.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: stock_feature_importance.png")

def main():
    print("="*80)
    print("STOCK MARKET PRICE FORECASTING SYSTEM")
    print("="*80)
    
    print("\n[1] Generating stock market data...")
    df = generate_stock_data(n_days=500)
    
    print("\n[2] Calculating technical indicators...")
    df_indicators = calculate_technical_indicators(df)
    df_indicators.to_csv('/home/ubuntu/stock_with_indicators.csv', index=False)
    
    print("\n[3] Preparing features for forecasting...")
    X_train, X_test, y_train, y_test, scaler, df_clean = prepare_features_for_forecasting(df_indicators)
    print(f"Training set size: {len(X_train)}, Test set size: {len(X_test)}")
    
    print("\n[4] Training forecasting models...")
    results_df, predictions, y_test_final, gb_model = train_forecasting_models(X_train, X_test, y_train, y_test)
    print("\nModel Results:")
    print(results_df.to_string())
    
    print("\n[5] Generating visualizations...")
    generate_visualizations(df, df_indicators, results_df, predictions, y_test_final, gb_model)
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE - All files generated successfully")
    print("="*80)

if __name__ == "__main__":
    main()
