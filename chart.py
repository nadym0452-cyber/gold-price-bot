import os
import json
import requests
import pandas as pd
import mplfinance as mpf
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
HISTORY_FILE = "price_history.json"
CHART_FILE = "gold_chart.png"


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
    color_hex = "#0ECB81" if change >= 0 else "#F6465D"

    mc = mpf.make_marketcolors(
        up="#0ECB81",
        down="#F6465D",
        edge="inherit",
        wick="inherit",
        volume="inherit",
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        facecolor="#0B0E11",
        figcolor="#0B0E11",
        edgecolor="#0B0E11",
        gridcolor="#1E2329",
        gridstyle="-",
        gridaxis="horizontal",
        y_on_right=True,
        rc={
            "font.size": 11,
            "axes.labelcolor": "#848E9C",
            "xtick.color": "#848E9C",
            "ytick.color": "#848E9C",
            "text.color": "#EAECEF",
            "axes.edgecolor": "#1E2329",
        },
    )

    title = (
        f"\nGOLD/EGP        {last_price:,.2f}  "
        f"{sign}{change:,.2f}  ({sign}{change_pct:.2f}%)"
    )

    fig, axlist = mpf.plot(
        candles,
        type="candle",
        style=style,
        title=title,
        ylabel="EGP / Gram",
        figsize=(11, 6.5),
        tight_layout=True,
        returnfig=True,
    )

    fig.savefig(CHART_FILE, dpi=170, facecolor="#0B0E11", bbox_inches="tight")


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
