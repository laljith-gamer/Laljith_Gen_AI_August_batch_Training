def add_book(catalog, book_id, title, author, year):
    catalog[book_id] = (title, author, year)
    return catalog


def borrow_book(catalog, borrowed_books, book_id):
    if book_id in catalog and book_id not in borrowed_books:
        borrowed_books.append(book_id)
        return True
    return False


def return_book(borrowed_books, book_id):
    if book_id in borrowed_books:
        borrowed_books.remove(book_id)
        return True
    return False


def register_member(members, member_id):
    members.add(member_id)


def show_available(catalog, borrowed_books):
    for book_id, details in catalog.items():
        if book_id not in borrowed_books:
            print(f"Book ID: {book_id}, Title: {details[0]}, Author: {details[1]}, Year: {details[2]}")


def main():
    catalog = {}
    borrowed_books = []
    members = set()

    add_book(catalog, 1, "The Great Gatsby", "F. Scott Fitzgerald", 1925)
    add_book(catalog, 2, "To Kill a Mockingbird", "Harper Lee", 1960)
    add_book(catalog, 3, "1984", "George Orwell", 1949)
    add_book(catalog, 4, "Pride and Prejudice", "Jane Austen", 1813)

    register_member(members, 101)
    register_member(members, 102)
    register_member(members, 103)
    register_member(members, 101)

    borrow_book(catalog, borrowed_books, 1)
    borrow_book(catalog, borrowed_books, 3)

    return_book(borrowed_books, 1)

    print("Available Books:")
    print("-" * 50)
    show_available(catalog, borrowed_books)
    print("-" * 50)
    print(f"Registered Members: {sorted(members)}")


if __name__ == "__main__":
    main()
