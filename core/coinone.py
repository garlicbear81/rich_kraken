import base64
import hashlib
import hmac
import json
import os
import uuid

import requests

ACCESS_TOKEN = None
SECRET_KEY = None


def init(access_key, secret_key):
    global ACCESS_TOKEN, SECRET_KEY
    ACCESS_TOKEN = access_key
    SECRET_KEY = bytes(secret_key, "utf-8")


def get_encoded_payload(payload):
    payload["nonce"] = str(uuid.uuid4())

    dumped_json = json.dumps(payload)
    encoded_json = base64.b64encode(bytes(dumped_json, "utf-8"))
    return encoded_json


def get_signature(encoded_payload):
    signature = hmac.new(SECRET_KEY, encoded_payload, hashlib.sha512)
    return signature.hexdigest()


def get_response(action, method="post", payload=None, public=False):
    url = f"https://api.coinone.co.kr/{action}"

    headers = {"Accept": "application/json"}
    if not public:
        encoded_payload = get_encoded_payload(payload)
        headers.update(
            {
                "X-COINONE-PAYLOAD": encoded_payload,
                "X-COINONE-SIGNATURE": get_signature(encoded_payload),
            }
        )

    return requests.request(method, url, headers=headers, json=payload).json()


def get_balances():
    data = get_response(
        action="/v2.1/account/balance/all",
        payload={"access_token": ACCESS_TOKEN},
    )
    return {balance["currency"]: balance for balance in data["balances"]}


def get_ticker(ticker):
    return get_response(f"/public/v2/ticker_new/KRW/{ticker}", method="get", public=True)["tickers"][0]


def buy_ticker(ticker, amount_krw):
    return get_response(
        action="/v2.1/order",
        payload={
            "access_token": ACCESS_TOKEN,
            "quote_currency": "KRW",
            "target_currency": ticker,
            "side": "BUY",
            "type": "MARKET",
            "amount": amount_krw,
        },
    )


def get_order_detail(order_id, target_currency):
    return get_response(
        action=f"/v2.1/order/detail",
        payload={
            "access_token": ACCESS_TOKEN,
            "order_id": order_id,
            "quote_currency": "KRW",
            "target_currency": target_currency,
        },
    )
