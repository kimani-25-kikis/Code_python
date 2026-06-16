# pizza = {
#     'name': 'Margherita Pizza',
#     'price': 8.9,
#     'calories_per_slice': 250,
#     'toppings': ['mozzarella', 'basil'],
#     'total_time': 20
# }
# pizza.update({ 'price': 15, 'total_time': 25 })
# print(pizza['name'])

# print(pizza.keys())
# print(pizza.values())
# print(pizza.items())

# pizza.update({ 'price': 15, 'total_time': 25 })

# products = {
#     'Laptop': 990,
#     'Smartphone': 600,
#     'Tablet': 250,
#     'Headphones': 70,
# }

# for product, price in products.items():
#     products[product] = round(price * 0.8)

# print(products)

products = {
    'Laptop': 990,
    'Smartphone': 600,
    'Tablet': 250,
    'Headphones': 70,
}

# for product in enumerate(products):
#     print(product)
# for index, product in enumerate(products):
#     print(index, product)

# for price in enumerate(products.values()):
#     print(price)

# for index, price in enumerate(products.values()):
#     print(index, price)

# for index, product in enumerate(products.items()):
#     print(index, product)
for index, product in enumerate(products.items(), 1):
    print(index, product)