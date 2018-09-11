#!/usr/bin/env python3
"""
Data models to hold data from db
"""

__author__ = "Samuel Whang"

class Store:
    __slots__ = ['name',]
    def __init__(self, store_name):
        self.name = store_name

class Card:
    __slots__ = ['number',]
    def __init__(self, card_number: str):
       self.number = card_number

class Product:
    def __init__(self, name: str, price: [int, float]):
        self.name = name
        self.name_format = '{}'
        self.price = float(price)
        self.price_format = '{:.2f}'

    @property
    def description(self):
        return self.name, self.price
    
    @property
    def formats(self):
        return self.name_format, self.price_format

    @property
    def format_criteria(self):
        return '{}{}{:.2f}'

if __name__ == "__main__":
    product = Product("example")
    print(product.description)
    print(f"{Card.__name__}: {Card.__slots__}")
    print(f"{Store.__name__}: {Store.__slots__}")
