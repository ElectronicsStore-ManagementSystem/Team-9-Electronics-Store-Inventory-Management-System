# Low-stock highlighting

An item is low stock when its quantity is greater than zero and less than or
equal to its reorder level. The inventory table highlights these rows with an
amber background, a left-side indicator, a `Low stock` badge, and a `Needs
reorder` label beside the quantity.

Items with zero quantity are marked `Out of stock` with a separate red row
indicator. Both indicators are recalculated whenever the inventory list is
loaded, so changes to quantity or reorder level are reflected after saving.

Managers can use the **Low stock** filter to show only items requiring
attention.
