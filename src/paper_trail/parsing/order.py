"""按坐标恢复阅读顺序。不依赖具体解析器。"""

from dataclasses import dataclass

# 通栏块要同时跨过页面左侧 35% 和右侧 65%，或者宽度达到页宽的 60%。
FULL_LEFT_RATIO = 0.35
FULL_RIGHT_RATIO = 0.65
FULL_WIDTH_RATIO = 0.60
# 右栏块的左边缘不小于页宽的 42%。
RIGHT_X0_RATIO = 0.42
# 页眉、页脚的判定边距，单位是点。
MARGIN_PT = 54.0
TABLE_OVERLAP_RATIO = 0.3


@dataclass(frozen=True)
class PlacedBlock:
    """一个带坐标的文本块或图片块。"""

    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    kind: str


@dataclass(frozen=True)
class OrderedBlock:
    """排好阅读顺序后的块。"""

    reading_order: int
    column: str
    region: str
    block: PlacedBlock


def column_of(block: PlacedBlock, page_width: float) -> str:
    """判断块属于左栏、右栏还是通栏。"""
    crosses_gutter = (
        block.x0 < FULL_LEFT_RATIO * page_width
        and block.x1 > FULL_RIGHT_RATIO * page_width
    )
    if crosses_gutter or (block.x1 - block.x0) >= FULL_WIDTH_RATIO * page_width:
        return "full"
    if block.x0 >= RIGHT_X0_RATIO * page_width:
        return "right"
    return "left"


def region_of(block: PlacedBlock, page_height: float, margin: float = MARGIN_PT) -> str:
    """标记页眉、页脚。贯穿整页的块仍算正文。"""
    touches_top = block.y0 < margin
    touches_bottom = block.y1 > page_height - margin
    if touches_top and touches_bottom:
        return "body"
    if touches_top:
        return "header"
    if touches_bottom:
        return "footer"
    return "body"


def overlaps_bbox(
    block: PlacedBlock,
    bbox: list[float],
    min_ratio: float = TABLE_OVERLAP_RATIO,
) -> bool:
    """块面积有足够比例落在 bbox 内时返回 True。"""
    x0, y0, x1, y1 = bbox
    ix0 = max(block.x0, x0)
    iy0 = max(block.y0, y0)
    ix1 = min(block.x1, x1)
    iy1 = min(block.y1, y1)
    if ix1 <= ix0 or iy1 <= iy0:
        return False
    intersection = (ix1 - ix0) * (iy1 - iy0)
    area = max((block.x1 - block.x0) * (block.y1 - block.y0), 1e-6)
    return intersection / area >= min_ratio


def order_blocks(
    blocks: list[PlacedBlock],
    page_width: float,
    page_height: float,
) -> list[OrderedBlock]:
    """先排通栏上方的左栏、再排右栏，然后插入通栏块。"""
    grouped = {"full": [], "left": [], "right": []}
    regions = []
    for block in blocks:
        column = column_of(block, page_width)
        grouped[column].append(block)
        regions.append(region_of(block, page_height))
    region_by_id = {id(block): region for block, region in zip(blocks, regions)}
    fulls = sorted(grouped["full"], key=lambda block: (block.y0, block.x0))

    def take(column: str, y_start: float, y_end: float) -> list[PlacedBlock]:
        chosen = [
            block
            for block in grouped[column]
            if y_start <= block.y0 < y_end
        ]
        return sorted(chosen, key=lambda block: (block.y0, block.x0))

    ordered: list[PlacedBlock] = []
    cursor = float("-inf")
    for full in fulls:
        ordered.extend(take("left", cursor, full.y0))
        ordered.extend(take("right", cursor, full.y0))
        ordered.append(full)
        cursor = full.y0
    ordered.extend(take("left", cursor, float("inf")))
    ordered.extend(take("right", cursor, float("inf")))
    return [
        OrderedBlock(index, column_of(block, page_width), region_by_id[id(block)], block)
        for index, block in enumerate(ordered)
    ]
