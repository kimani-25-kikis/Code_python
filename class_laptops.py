class Laptop:
   
    shop_name = "TechHub Computers"
    warranty_years = 2

    def __init__(self, brand, model, price):
        
        self.brand = brand
        self.model = model
        self.price = price

    def display_info(self):
        print(f"Shop: {Laptop.shop_name}")
        print(f"Laptop: {self.brand} {self.model}")
        print(f"Price: ${self.price}")
        print(f"Warranty: {Laptop.warranty_years} years")
        print("-" * 30)


laptop1 = Laptop("Dell", "Inspiron 15", 750)
laptop2 = Laptop("HP", "Pavilion", 650)
laptop3 = Laptop("Lenovo", "ThinkPad E14", 900)

laptop1.display_info()
laptop2.display_info()
laptop3.display_info()


print("Shop Name:", Laptop.shop_name)

Laptop.warranty_years = 3

print("\nAfter updating warranty:\n")

laptop1.display_info()
laptop2.display_info()
laptop3.display_info()