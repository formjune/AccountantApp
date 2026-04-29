import enum


__all__ = ("PromotionSourceEnum", "PaymentStatusEnum", "SpendingTypeEnum", "StaffTypeEnum", "DateRangeTypeEnum")


class PromotionSourceEnum(enum.Enum):

    employee = 0
    incubator = 1
    adviser = 2
    marketing = 3


class SpendingTypeEnum(enum.Enum):

    regular = 0
    onetime = 1


class PaymentStatusEnum(enum.Enum):

    unpaid = 0
    partial = 1
    complete = 2


class StaffTypeEnum(enum.Enum):

    insource = 0
    outsource = 1
    dismissed = 2


class DateRangeTypeEnum(enum.Enum):

    vacation = 0
    sick = 1
