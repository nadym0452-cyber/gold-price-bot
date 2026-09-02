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

    candles = df["price"].resample("15min").ohlc()
    candles = candles.dropna()
    candles.columns = ["Open", "High", "Low", "Close"]
    return candles


def draw_chart(candles):
    mc = mpf.make_marketcolors(
        up="#0ECB81",
        down="#F6465D",
        edge="inherit",
        wick="inherit",
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        facecolor="#161A25",
        figcolor="#161A25",
        gridcolor="#2B2F3A",
        gridstyle="--",
        y_on_right=True,
        rc={"font.size": 10, "axes.labelcolor": "white",
            "xtick.color": "white", "ytick.color": "white",
            "text.color": "white"},
    )

    mpf.plot(
        candles,
        type="candle",
        style=style,
        title="\nGold Price - Last 6 Hours",
        ylabel="EGP / Gram",
        savefig=dict(fname=CHART_FILE, dpi=150, bbox_inches="tight"),
    )


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
