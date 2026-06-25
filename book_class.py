# class Book:
#    def __init__(self, title, pages):
#        self.title = title
#        self.pages = pages

# book1 = Book("Built Wealth Like a Boss", 420)
# book2 = Book("Be Your Own Start", 420)

# print(len(book1)) # TypeError: object of type 'Book' has no len()
# print(str(book1))

class Book:
   def __init__(self, title, pages):
       self.title = title
       self.pages = pages

   def __len__(self):
       return self.pages

   def __str__(self):
       return f"'{self.title}' has {self.pages} pages"

   def __eq__(self, other):
       return self.pages == other.pages
  
book1 = Book("Built Wealth Like a Boss", 420)
book2 = Book("Be Your Own Start", 420)

print(len(book1)) 
print(len(book2)) 
print(str(book1))
print(str(book2)) 
print(book1 == book2)