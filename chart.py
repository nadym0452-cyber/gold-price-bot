import os
import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
HISTORY_FILE = "price_history.json"
CHART_FILE = "gold_chart.png"

BG = "#0B0E11"
GRID = "#1E2329"
TEXT_MAIN = "#EAECEF"
TEXT_MUTED = "#848E9C"
GREEN = "#0ECB81"
RED = "#F6465D"
TREND_COLOR = "#F0B90B"


def load_history():
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)


def build_candles(history, hours=6):
    df = pd.DataFrame(history)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    df = df[df.index >= cutoff]

    candles = df["price"].resample("1h").ohlc()
    candles = candles.dropna()
    candles.columns = ["Open", "High", "Low", "Close"]
    return candles


def draw_chart(candles):
    last_price = candles["Close"].iloc[-1]
    first_price = candles["Open"].iloc[0]
    change = last_price - first_price
    change_pct = (change / first_price) * 100
    sign = "+" if change >= 0 else ""
    header_color = GREEN if change >= 0 else RED

    high_val = candles["High"].max()
    low_val = candles["Low"].min()
    high_time = candles["High"].idxmax()
    low_time = candles["Low"].idxmin()

    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=170)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    x = mdates.date2num(candles.index.to_pydatetime())
    width = (x[1] - x[0]) * 0.55 if len(x) > 1 else 0.02

    for xi, (_, row) in zip(x, candles.iterrows()):
        color = GREEN if row["Close"] >= row["Open"] else RED
        ax.plot([xi, xi], [row["Low"], row["High"]], color=color, linewidth=1.3, zorder=2)
        body_low = min(row["Open"], row["Close"])
        body_high = max(row["Open"], row["Close"])
        height = max(body_high - body_low, (high_val - low_val) * 0.004)
        rect = Rectangle(
            (xi - width / 2, body_low), width, height,
            facecolor=color, edgecolor=color, zorder=3,
        )
        ax.add_patch(rect)

    trend = candles["Close"].rolling(2, min_periods=1).mean()
    ax.plot(x, trend.values, color=TREND_COLOR, linewidth=1.6,
            linestyle="-", alpha=0.85, zorder=4, label="Trend")

    ax.scatter([mdates.date2num(high_time)], [high_val], s=55, color=GREEN,
               edgecolor=BG, linewidth=1.5, zorder=5)
    ax.annotate(f"High  {high_val:,.0f}", (mdates.date2num(high_time), high_val),
                textcoords="offset points", xytext=(0, 12), ha="center",
                fontsize=10, color=GREEN, fontweight="bold")

    ax.scatter([mdates.date2num(low_time)], [low_val], s=55, color=RED,
               edgecolor=BG, linewidth=1.5, zorder=5)
    ax.annotate(f"Low  {low_val:,.0f}", (mdates.date2num(low_time), low_val),
                textcoords="offset points", xytext=(0, -18), ha="center",
                fontsize=10, color=RED, fontweight="bold")

    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.tick_params(colors=TEXT_MUTED, labelsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.yaxis.tick_right()
    ax.set_ylabel("EGP / Gram", color=TEXT_MUTED, fontsize=11)
    ax.yaxis.set_label_position("right")

    pad = (high_val - low_val) * 0.15
    ax.set_ylim(low_val - pad, high_val + pad)

    fig.text(0.06, 0.94, "GOLD / EGP", fontsize=15, color=TEXT_MAIN,
              fontweight="bold", va="top")
    fig.text(0.06, 0.885,
              f"{last_price:,.2f}   {sign}{change:,.2f}  ({sign}{change_pct:.2f}%)",
              fontsize=13, color=header_color, va="top", fontweight="bold")

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fig.text(0.94, 0.03, f"Last update: {now_str}", fontsize=8.5,
              color=TEXT_MUTED, ha="right")

    fig.subplots_adjust(left=0.07, right=0.9, top=0.82, bottom=0.12)
    fig.savefig(CHART_FILE, facecolor=BG)
    plt.close(fig)


def send_chart():
    caption = "هذا شكل مؤشر الذهب خلال الـ6 ساعات الماضية"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(CHART_FILE, "rb") as photo:
        requests.post(
            url,
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"photo": photo},
            timeout=30,
        )


def main():
    history = load_history()
    candles = build_candles(history, hours=6)
    if len(candles) < 2:
        print("Not enough data yet")
        return
    draw_chart(candles)
    send_chart()


if __name__ == "__main__":
    main()
