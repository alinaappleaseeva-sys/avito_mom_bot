from enum import Enum

class ItemCategory(str, Enum):
    STROLLER = "stroller"
    CLOTHES = "clothes"
    SHOES = "shoes"
    TOYS = "toys"
    OTHER = "other"

class ItemCondition(str, Enum):
    NEW = "new"
    PERFECT = "perfect"
    GOOD = "good"
    FAIR = "fair"

class SellSpeed(str, Enum):
    FAST = "fast"
    OPTIMAL = "optimal"

class ItemStatus(str, Enum):
    DRAFT = "draft"
    PENDING_MODERATION = "pending_moderation"
    ACTIVE = "active"
    REJECTED = "rejected"
    ARCHIVED = "archived"
