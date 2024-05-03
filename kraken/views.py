import json
from datetime import timedelta

import pandas as pd
from django.utils import timezone
from django.views.generic import TemplateView

from .models import Kraken


class IndexView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        kraken = Kraken()
        balance = kraken.get_account_balance()

        pair = "XXBTZEUR"
        ticker = kraken.get_ticker(pair)

        # average of ask, bid
        price = (float(ticker["a"][pair][0]) + float(ticker["b"][pair][0])) / 2
        balance["XXBT"]["price"] = price

        for v in balance.values():
            if "price" in v:
                v["my_price"] = f"{v['price'] * v['amount']:,.2f} Euros"

        data["balance"] = balance
        data["chart_data"] = []

        if self.request.GET.get("chart") == "1":
            # trade history
            end = timezone.now()
            end_ts = end.timestamp()
            days = 365
            days = 60
            start_ts = (end - timedelta(days=days)).timestamp()

            all_trades = []
            while True:
                print(start_ts, end_ts)
                trades = kraken.get_trades(start=start_ts, end=end_ts)[0]
                all_trades.append(trades)

                # row count
                if trades.shape[0] == 0:
                    break

                end_ts = trades["time"][-1] - 1
                if end_ts <= start_ts:
                    break

            # 모든 페이지의 데이터를 하나의 DataFrame으로 결합
            df = pd.concat(all_trades, ignore_index=True)

            df[df["pair"] == "XXBTZEUR"]
            df["spent"] = df["cost"] + df["fee"]

            first_row = df.iloc[0]
            euro_balance = balance["ZEUR"]["amount"] - first_row["spent"]
            btc_balance = balance["XXBT"]["amount"] + first_row["vol"]

            df["euro"] = df["spent"].cumsum() + euro_balance
            df["btc"] = btc_balance - df["vol"].cumsum()
            df["btc_euro"] = df["btc"] * df["price"]
            df["total_euro"] = df["btc_euro"] + df["euro"]
            df["dtime"] = pd.to_datetime(df["time"], unit="s")
            df["date"] = df["dtime"].dt.strftime("%Y-%m-%d")

            reversed_df = (
                df[["date", "euro", "btc", "price", "btc_euro", "total_euro"]].iloc[::-1].reset_index(drop=True)
            )
            json_data = reversed_df.to_json(orient="records")
            data["chart_data"] = json.dumps(json_data)

            recent_row = df.iloc[0]
            old_row = df.iloc[-1]
            bought_btc = recent_row["btc"] - old_row["btc"]
            diff_total_euro = recent_row["total_euro"] - old_row["total_euro"]
            profit = diff_total_euro / old_row["total_euro"] * 100
            balance["BTC"] = {
                "bought amount": bought_btc,
                "increased BTC in Euro": recent_row["btc_euro"] - old_row["btc_euro"],
                "spent Euro balance": old_row["euro"] - recent_row["euro"],
                "Total increased value in Euro": diff_total_euro,
                "Profit": f"{profit:.2f} %",
            }

        return data
