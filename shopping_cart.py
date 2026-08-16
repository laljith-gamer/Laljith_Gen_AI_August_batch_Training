
def add_item(item, cart=None):
    if cart is None:
        cart = []
    cart.append(item)
    return cart


def create_cart(owner, discount=0):
    return {"owner": owner, "items": [], "discount": discount}


def add_to_cart(cart, name, price, qty=1):
    cart["items"].append({"name": name, "price": price, "qty": qty})
    return cart


def update_price(price_tuple, new_price):
    try:
        price_tuple[0] = new_price
    except TypeError as e:
        print(f"TypeError: {e}")
        print("Tuples are immutable - their elements cannot be changed after creation.")


def calculate_total(cart):
    subtotal = 0
    for item in cart["items"]:
        subtotal += item["price"] * item["qty"]
    discount_amount = subtotal * (cart["discount"] / 100)
    final_total = subtotal - discount_amount
    return final_total


def print_cart(cart):
    print(f"\nCart Owner: {cart['owner']} (Discount: {cart['discount']}%)")
    print("Items:")
    for item in cart["items"]:
        print(f"  - {item['name']}: ${item['price']} x {item['qty']} = ${item['price'] * item['qty']}")
    total = calculate_total(cart)
    print(f"Total (after discount): ${total}")
    print("-" * 50)


def main():
    print("=== Shopping Cart Demo ===\n")
    
    print("Part A Output Prediction:")
    print("Predicted sequence: ['apple'], ['apple', 'banana'], ['bread', 'milk'], ['apple', 'banana', 'eggs']")
    
    print("\nVerifying Part A:")
    def buggy_add_item(item, cart=[]):
        cart.append(item)
        return cart
    
    result1 = buggy_add_item("apple")
    print(f"add_item('apple') -> {result1}")
    
    result2 = buggy_add_item("banana")
    print(f"add_item('banana') -> {result2}")
    
    result3 = buggy_add_item("milk", cart=["bread"])
    print(f"add_item('milk', cart=['bread']) -> {result3}")
    
    result4 = buggy_add_item("eggs")
    print(f"add_item('eggs') -> {result4}")
    
    print("\n" + "=" * 50)
    print("Part B - Fixed add_item Function:")
    print("=" * 50)
    print("Using None as default and creating new list inside function body")
    
    result5 = add_item("apple")
    print(f"add_item('apple') -> {result5}")
    
    result6 = add_item("banana")
    print(f"add_item('banana') -> {result6}")
    
    result7 = add_item("milk", cart=["bread"])
    print(f"add_item('milk', cart=['bread']) -> {result7}")
    
    result8 = add_item("eggs")
    print(f"add_item('eggs') -> {result8}")
    
    print("\n" + "=" * 50)
    print("Part C - Complete Shopping Cart")
    print("=" * 50)
    
    cart1 = create_cart("Alice", discount=10)
    add_to_cart(cart1, "Apple", 2.50, 3)
    add_to_cart(cart1, "Bread", 1.75, 2)
    add_to_cart(cart1, "Milk", 3.00)
    
    cart2 = create_cart("Bob", discount=15)
    add_to_cart(cart2, "Eggs", 4.00, 1)
    add_to_cart(cart2, "Cheese", 5.50, 2)
    
    print("Adding item to cart1 does not affect cart2:")
    add_to_cart(cart1, "Butter", 3.25, 1)
    
    print_cart(cart1)
    print_cart(cart2)
    
    print("\n" + "=" * 50)
    print("Tuple Immutability Demo:")
    print("=" * 50)
    price_tuple = (10.0, 20.0, 30.0)
    print(f"Original tuple: {price_tuple}")
    print("Attempting to modify first element...")
    update_price(price_tuple, 15.0)
    
    print("\nDemonstrating Independent Carts:")
    print(f"Cart 1 items count: {len(cart1['items'])}")
    print(f"Cart 2 items count: {len(cart2['items'])}")
    print("Carts are independent - adding to one doesn't affect the other.")


if __name__ == "__main__":
    main()
