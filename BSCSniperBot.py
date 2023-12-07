#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    *******************************************************************************************
    BSCSniperBot: Binance Smart Chain Token Sniper Bot
    Author: Ali Toori
    Website: https://botflocks.com/
    *******************************************************************************************
"""
import time
import json
import os
import pyfiglet
import logging.config
from multiprocessing import freeze_support
from pathlib import Path
import pandas as pd
from web3 import Web3
from bscscan import BscScan
import asyncio


class BSCSniperBot:
    def __init__(self):
        self.logged_in = False
        self.stopped = False
        self.PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
        self.file_settings = str(self.PROJECT_ROOT / 'BSCRes/Settings.json')
        self.file_contract = str(self.PROJECT_ROOT / 'BSCRes/TokenAddress.csv')
        self.settings = self.get_settings()
        self.bsc_api_key = self.settings['API-Key']
        self.LOGGER = self.get_logger()
        self.web3 = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))
        self.token_to_buy = None
        self.contract = None
        self.contract_buy = None
        self.BNB_PAIR_ADDRESS = None

    # Get self.LOGGER
    @staticmethod
    def get_logger():
        """
        Get logger file
        :return: LOGGER
        """
        logging.config.dictConfig({
            "version": 1,
            "disable_existing_loggers": False,
            'formatters': {
                'colored': {
                    '()': 'colorlog.ColoredFormatter',  # colored output
                    # --> %(log_color)s is very important, that's what colors the line
                    'format': '[%(asctime)s,%(lineno)s] %(log_color)s[%(message)s]',
                    'log_colors': {
                        'DEBUG': 'green',
                        'INFO': 'cyan',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'bold_red',
                    },
                },
                'simple': {
                    'format': '[%(asctime)s,%(lineno)s] [%(message)s]',
                },
            },
            "handlers": {
                "console": {
                    "class": "colorlog.StreamHandler",
                    "level": "INFO",
                    "formatter": "colored",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "simple",
                    "filename": "BSCSniperBot.log"
                },
            },
            "root": {"level": "INFO",
                     "handlers": ["console", "file"]
                     }
        })
        return logging.getLogger()

    @staticmethod
    def enable_cmd_colors():
        from sys import platform
        if platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    @staticmethod
    def banner():
        pyfiglet.print_figlet(text='____________ BSCSniperBot\n', colors='RED')
        print('Author: Ali Toori\n'
              'Website: https://botflocks.com/\n'
              '************************************************************************')

    # Get settings
    def get_settings(self):
        if os.path.isfile(self.file_settings):
            with open(self.file_settings, 'r') as f:
                settings = json.load(f)
            return settings

    # Get contract address
    def get_token_address(self):
        df = pd.read_csv(self.file_contract, index_col=None)
        if not len(df):
            pass
        else:
            return df.iloc[0]['TokenToBuy']

    # If conditions are met we buy the token
    def buy(self):
        for i, wallet in enumerate(self.settings["Wallets"]):
            sender_address = self.web3.toChecksumAddress(wallet)  # the address which buys the token
            nonce = self.web3.eth.get_transaction_count(sender_address)
            for j, amount_to_buy in enumerate(self.settings["AmountToBuy"]):
                pancakeswap2_txn = self.contract_buy.functions.swapExactETHForTokens(
                    amount_to_buy,  # set to 0, or specify minimum amount of token you want to receive - consider decimals!!!
                    [self.BNB_PAIR_ADDRESS, self.token_to_buy],
                    sender_address,
                    (int(time.time()) + 10000)
                ).buildTransaction({
                    'from': sender_address,
                    'value': self.web3.toWei(float(self.settings["BNB-To-Spend"]), 'ether'),  # This is the Token(BNB) amount you want to Swap from
                    'gasPrice': self.web3.toWei(int(self.settings["Gas-Price"]), 'gwei'),
                    'nonce': nonce,
                })
                signed_txn = self.web3.eth.account.sign_transaction(pancakeswap2_txn, private_key=self.settings["Private-Keys"][i])
                tx_token = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
                print("Snipe was successful, bought: " + self.web3.toHex(tx_token))

    # define function to handle events and print to the console
    def handle_event(self, event):
        pair = Web3.toJSON(event)
        print(pair)
        token0 = str(Web3.toJSON(event['args']['token1']))
        token1 = str(Web3.toJSON(event['args']['token0']))
        print("Token0: " + token0)
        print("Token1: " + token1)
        bnb_upper = self.BNB_PAIR_ADDRESS.upper()
        token_to_buy_upper = self.token_to_buy.upper()
        if (token0.upper().strip('"') == bnb_upper and token1.upper().strip('"') == token_to_buy_upper):
            print("pair detected")
            self.buy()
        elif (token0.upper().strip('"') == token_to_buy_upper and token1.upper().strip('"') == bnb_upper):
            print("pair detected")
            self.buy()
        else:
            print("next pair")

    # asynchronous defined function to loop
    # this loop sets up an event filter and is looking for new entires for the "PairCreated" event
    # this loop runs on a poll interval
    async def log_loop(self, event_filter, poll_interval):
        while True:
            for PairCreated in event_filter.get_new_entries():
                self.handle_event(PairCreated)
            await asyncio.sleep(poll_interval)

    def main(self):
        freeze_support()
        self.enable_cmd_colors()
        self.banner()
        self.LOGGER.info(f'BSCSniperBot launched')
        self.LOGGER.info(f'Web3 connected: {self.web3.isConnected()}')
        with BscScan(api_key=self.bsc_api_key, asynchronous=False) as client:
            print(f'BNBBUSD current price: {client.get_bnb_last_price()["ethusd"]}')
            while True:
                if self.get_token_address():
                    self.token_to_buy = self.get_token_address()
                    break
            bsc_factory_address = str(self.settings['BSC-Factory-Address'])
            bsc_router_address = str(self.settings['BSC-Router-Address'])
            bsc_factory_abi = json.loads(client.get_contract_abi(bsc_factory_address))
            bsc_router_abi = json.loads(client.get_contract_abi(bsc_router_address))
            self.contract = self.web3.eth.contract(address=bsc_factory_address, abi=bsc_factory_abi)
            self.contract_buy = self.web3.eth.contract(address=bsc_router_address, abi=bsc_router_abi)
            self.BNB_PAIR_ADDRESS = self.web3.toChecksumAddress(self.settings["BNB-Pair-Address"])
            # create a filter for the latest block and look for the "PairCreated" event for the BSC factory contract
            # run an async loop
            # try to run the log_loop function above every 2 seconds
            event_filter = self.contract_buy.events.PairCreated.createFilter(fromBlock='latest')
            # block_filter = web3.eth.filter('latest')
            # tx_filter = web3.eth.filter('pending')
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(
                    asyncio.gather(
                        self.log_loop(event_filter, 2)))
                # log_loop(block_filter, 2),
                # log_loop(tx_filter, 2)))
            finally:
                # close loop to free up system resources
                loop.close()


if __name__ == '__main__':
    bsc_sniper_bot = BSCSniperBot()
    bsc_sniper_bot.main()

