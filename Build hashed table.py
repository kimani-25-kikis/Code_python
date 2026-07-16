class HashTable:
    def __init__(self):
        self.collection = {}

    def hash(self, string):
        return sum(ord(char) for char in string)

    def add(self, key, value):
        hashed_key = self.hash(key)

        if hashed_key not in self.collection:
            self.collection[hashed_key] = {}

        self.collection[hashed_key][key] = value

    def remove(self, key):
        hashed_key = self.hash(key)

        if hashed_key in self.collection:
            if key in self.collection[hashed_key]:
                del self.collection[hashed_key][key]

                
                if not self.collection[hashed_key]:
                    del self.collection[hashed_key]

    def lookup(self, key):
        hashed_key = self.hash(key)

        if hashed_key in self.collection:
            return self.collection[hashed_key].get(key)

        return None



hash_table = HashTable()

hash_table.add("golf", "sport")
hash_table.add("dear", "friend")
hash_table.add("read", "book")
hash_table.add("fcc", "coding")
hash_table.add("cfc", "chemical")

print(hash_table.collection)
# {424: {'golf': 'sport'}, 412: {'dear': 'friend', 'read': 'book'}, 300: {'fcc': 'coding', 'cfc': 'chemical'}}

print(hash_table.lookup("golf"))  # sport
print(hash_table.lookup("cfc"))   # chemical
print(hash_table.lookup("xyz"))   # None

hash_table.remove("golf")
print(hash_table.lookup("golf"))  # None

hash_table.remove("unknown")      # No error
print(hash_table.collection)