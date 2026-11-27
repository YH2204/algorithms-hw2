"""Hash tables using separate chaining and linear probing."""


class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value, next_node=None):
        self.key = key
        self.value = value
        self.next = next_node


class ChainingHashTable:
    """A hash table whose buckets are singly linked lists."""

    def __init__(self, max_load=0.75):
        self.buckets = [None] * 16
        self._size = 0
        self.max_load = max_load

    @property
    def load_factor(self):
        return self._size / len(self.buckets)

    def _index(self, key):
        value = 0
        for character in key:
            value = (31 * value + ord(character)) % len(self.buckets)
        return value

    @staticmethod
    def _validate_key(key):
        if not isinstance(key, str):
            raise TypeError("키는 문자열이어야 합니다")

    def put(self, key, value):
        self._validate_key(key)
        index = self._index(key)
        node = self.buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        self.buckets[index] = _Node(key, value, self.buckets[index])
        self._size += 1
        if self.max_load is not None and self.load_factor > self.max_load:
            self._resize()

    def _resize(self):
        old_buckets = self.buckets
        self.buckets = [None] * (len(old_buckets) * 2)
        for head in old_buckets:
            node = head
            while node is not None:
                index = self._index(node.key)
                self.buckets[index] = _Node(
                    node.key,
                    node.value,
                    self.buckets[index],
                )
                node = node.next

    def find(self, key):
        self._validate_key(key)
        node = self.buckets[self._index(key)]
        cost = 0
        while node is not None:
            cost += 1
            if node.key == key:
                return True, node.value, cost
            node = node.next
        return False, None, cost

    def get(self, key):
        found, value, _ = self.find(key)
        if found:
            return value
        return None

    def delete(self, key):
        self._validate_key(key)
        index = self._index(key)
        node = self.buckets[index]
        previous = None
        while node is not None:
            if node.key == key:
                if previous is None:
                    self.buckets[index] = node.next
                else:
                    previous.next = node.next
                self._size -= 1
                return node.value
            previous = node
            node = node.next
        return None

    def __contains__(self, key):
        found, _, _ = self.find(key)
        return found

    def __len__(self):
        return self._size


_DELETED = object()


class LinearProbingHashTable:
    """A hash table that resolves collisions with linear probing."""

    def __init__(self, max_load=0.5):
        self.slots = [None] * 16
        self._size = 0
        self.max_load = max_load

    @property
    def load_factor(self):
        return self._size / len(self.slots)

    @staticmethod
    def _validate_key(key):
        if not isinstance(key, str):
            raise TypeError("키는 문자열이어야 합니다")

    def _index(self, key):
        value = 0
        for character in key:
            value = (31 * value + ord(character)) % len(self.slots)
        return value

    def _locate(self, key):
        start = self._index(key)
        for offset in range(len(self.slots)):
            index = (start + offset) % len(self.slots)
            entry = self.slots[index]
            if entry is None:
                return False, None, offset + 1
            if entry is not _DELETED and entry[0] == key:
                return True, index, offset + 1
        return False, None, len(self.slots)

    def find(self, key):
        self._validate_key(key)
        found, index, cost = self._locate(key)
        if found:
            return True, self.slots[index][1], cost
        return False, None, cost

    def get(self, key):
        found, value, _ = self.find(key)
        if found:
            return value
        return None

    def put(self, key, value):
        self._validate_key(key)
        start = self._index(key)
        first_deleted = None

        for offset in range(len(self.slots)):
            index = (start + offset) % len(self.slots)
            entry = self.slots[index]
            if entry is None:
                target = first_deleted if first_deleted is not None else index
                self.slots[target] = (key, value)
                self._size += 1
                self._grow_if_needed()
                return
            if entry is _DELETED:
                if first_deleted is None:
                    first_deleted = index
                continue
            if entry[0] == key:
                self.slots[index] = (key, value)
                return

        if first_deleted is not None:
            self.slots[first_deleted] = (key, value)
            self._size += 1
            self._grow_if_needed()
            return
        raise OverflowError("해시 테이블이 가득 찼습니다")

    def _grow_if_needed(self):
        if self.max_load is not None and self.load_factor > self.max_load:
            self._resize()

    def _resize(self):
        old_slots = self.slots
        self.slots = [None] * (len(old_slots) * 2)
        for entry in old_slots:
            if entry is not None and entry is not _DELETED:
                self._insert_without_resize(entry[0], entry[1])

    def _insert_without_resize(self, key, value):
        start = self._index(key)
        for offset in range(len(self.slots)):
            index = (start + offset) % len(self.slots)
            if self.slots[index] is None:
                self.slots[index] = (key, value)
                return
        raise OverflowError("해시 테이블이 가득 찼습니다")

    def delete(self, key):
        self._validate_key(key)
        found, index, _ = self._locate(key)
        if not found:
            return None
        value = self.slots[index][1]
        self.slots[index] = _DELETED
        self._size -= 1
        return value

    def __contains__(self, key):
        found, _, _ = self.find(key)
        return found

    def __len__(self):
        return self._size
