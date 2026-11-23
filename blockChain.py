import hashlib
import time
from typing import List, Dict

class Block:
    def __init__(self, index: int, transactions: List[Dict], previous_hash: str, nonce: int = 0):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = f"{self.index}{self.timestamp}{self.transactions}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

class Blockchain:
    def __init__(self, difficulty: int = 4):
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict] = []
        self.difficulty = difficulty
        self.mining_reward = 10.0
        self.create_genesis_block()

    def create_genesis_block(self) -> None:
        genesis_block = Block(0, [], "0")
        self.chain.append(genesis_block)

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, sender: str, recipient: str, amount: float) -> bool:
        if amount <= 0:
            return False
        if sender != "network" and self.get_balance(sender) < amount:
            return False
        self.pending_transactions.append({
            "sender": sender,
            "recipient": recipient,
            "amount": amount
        })
        return True

    def mine_pending_transactions(self, miner_address: str) -> None:
        block = Block(
            len(self.chain),
            self.pending_transactions.copy(),
            self.get_latest_block().hash
        )
        block = self.proof_of_work(block)
        self.chain.append(block)
        self.pending_transactions = [{
            "sender": "network",
            "recipient": miner_address,
            "amount": self.mining_reward
        }]

    def proof_of_work(self, block: Block) -> Block:
        target = "0" * self.difficulty
        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash = block.calculate_hash()
        return block

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
            if not current.hash.startswith("0" * self.difficulty):
                return False
        return True

    def get_balance(self, address: str) -> float:
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx["sender"] == address:
                    balance -= tx["amount"]
                if tx["recipient"] == address:
                    balance += tx["amount"]
        for tx in self.pending_transactions:
            if tx["sender"] == address:
                balance -= tx["amount"]
            if tx["recipient"] == address:
                balance += tx["amount"]
        return balance

    def print_chain(self) -> None:
        for block in self.chain:
            print(f"Block {block.index}")
            print(f"  Hash: {block.hash}")
            print(f"  Previous: {block.previous_hash}")
            print(f"  Nonce: {block.nonce}")
            print(f"  Transactions: {block.transactions}")
            print("-" * 50)

if __name__ == "__main__":
    blockchain = Blockchain(difficulty=4)

    blockchain.add_transaction("Alice", "Bob", 50)
    blockchain.add_transaction("Alice", "Charlie", 30)

    print("Mining block 1...")
    blockchain.mine_pending_transactions("Miner1")

    blockchain.add_transaction("Bob", "Dave", 20)
    blockchain.add_transaction("Charlie", "Eve", 15)

    print("Mining block 2...")
    blockchain.mine_pending_transactions("Miner1")

    print("\nBlockchain valid:", blockchain.is_chain_valid())
    print("\nBalances:")
    for person in ["Alice", "Bob", "Charlie", "Dave", "Eve", "Miner1"]:
        print(f"  {person}: {blockchain.get_balance(person)}")

    print("\nFull chain:")
    blockchain.print_chain()