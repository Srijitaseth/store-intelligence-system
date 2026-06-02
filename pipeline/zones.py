def point_inside_rectangle(point_x, point_y, rectangle):
    x1, y1, x2, y2 = rectangle

    return x1 <= point_x <= x2 and y1 <= point_y <= y2


def get_zone_for_point(point_x, point_y, zones):
    for zone_id, rectangle in zones.items():
        if point_inside_rectangle(point_x, point_y, rectangle):
            return zone_id

    return None