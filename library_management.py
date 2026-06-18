library = {
    "978-0135166307": {
        "title": "Python Crash Course",
        "author": "Eric Matthes",
        "copies": 3
    },
    "978-1492051367": {
        "title": "Fluent Python",
        "author": "Luciano Ramalho",
        "copies": 2
    }
}


def view_books():
    print("\nLIBRARY INVENTORY")
    print("-" * 50)

    if not library:
        print("No books available.")
        return

    for isbn, book in library.items():
        print(f"ISBN: {isbn}")
        print(f"Title: {book['title']}")
        print(f"Author: {book['author']}")
        print(f"Copies Available: {book['copies']}")
        print("-" * 50)


def add_book():
    isbn = input("Enter ISBN: ")

    if isbn in library:
        print("Book already exists.")
        return

    title = input("Enter title: ")
    author = input("Enter author: ")
    copies = int(input("Enter number of copies: "))

    library[isbn] = {
        "title": title,
        "author": author,
        "copies": copies
    }

    print("Book added successfully.")


def search_book():
    isbn = input("Enter ISBN to search: ")

    if isbn in library:
        book = library[isbn]

        print("\nBOOK FOUND")
        print(f"Title: {book['title']}")
        print(f"Author: {book['author']}")
        print(f"Copies: {book['copies']}")
    else:
        print("Book not found.")


def borrow_book():
    isbn = input("Enter ISBN to borrow: ")

    if isbn not in library:
        print("Book not found.")
        return

    if library[isbn]["copies"] > 0:
        library[isbn]["copies"] -= 1
        print("Book borrowed successfully.")
    else:
        print("No copies available.")


def return_book():
    isbn = input("Enter ISBN to return: ")

    if isbn not in library:
        print("Book not found.")
        return

    library[isbn]["copies"] += 1
    print("Book returned successfully.")


def remove_book():
    isbn = input("Enter ISBN to remove: ")

    if isbn in library:
        del library[isbn]
        print("Book removed.")
    else:
        print("Book not found.")


while True:
    print("\n===== LIBRARY MENU =====")
    print("1. View Books")
    print("2. Add Book")
    print("3. Search Book")
    print("4. Borrow Book")
    print("5. Return Book")
    print("6. Remove Book")
    print("7. Exit")

    choice = input("Choose an option: ")

    if choice == "1":
        view_books()

    elif choice == "2":
        add_book()

    elif choice == "3":
        search_book()

    elif choice == "4":
        borrow_book()

    elif choice == "5":
        return_book()

    elif choice == "6":
        remove_book()

    elif choice == "7":
        print("Goodbye!")
        break

    else:
        print("Invalid choice.")