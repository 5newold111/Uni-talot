"""
Blender ヘッドレスモードで呼び出されるスケール補正スクリプト。
呼び出し方: blender --background --python scale_model.py -- <input> <output> <W> <D> <H>
"""

import os
import sys

import bpy


def main():
    try:
        separator = sys.argv.index("--")
        argv = sys.argv[separator + 1 :]
    except ValueError:
        print("エラー: 引数が不足しています")
        sys.exit(1)

    if len(argv) < 5:
        print("使い方: -- <input_glb> <output_glb> <width_cm> <depth_cm> <height_cm>")
        sys.exit(1)

    input_path = argv[0]
    output_path = argv[1]
    width_cm = float(argv[2])
    depth_cm = float(argv[3])
    height_cm = float(argv[4])

    print(f"スケール補正開始: {input_path}")
    print(f"目標寸法: W{width_cm}cm × D{depth_cm}cm × H{height_cm}cm")

    bpy.ops.wm.read_factory_settings(use_empty=True)

    if not os.path.exists(input_path):
        print(f"エラー: 入力ファイルが存在しません: {input_path}")
        sys.exit(1)

    bpy.ops.import_scene.gltf(filepath=os.path.abspath(input_path))

    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not mesh_objects:
        print("エラー: GLBにメッシュオブジェクトが見つかりません")
        sys.exit(1)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objects[0]

    if len(mesh_objects) > 1:
        bpy.ops.object.join()

    obj = bpy.context.active_object
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    current_x_cm = obj.dimensions.x * 100
    current_y_cm = obj.dimensions.y * 100
    current_z_cm = obj.dimensions.z * 100

    if current_x_cm == 0 or current_y_cm == 0 or current_z_cm == 0:
        print("エラー: オブジェクトの寸法がゼロです")
        sys.exit(1)

    print(f"現在の寸法: X={current_x_cm:.1f}cm, Y={current_y_cm:.1f}cm, Z={current_z_cm:.1f}cm")

    sx = width_cm / current_x_cm
    sy = depth_cm / current_y_cm
    sz = height_cm / current_z_cm

    obj.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)

    print(f"適用スケール: X×{sx:.4f}, Y×{sy:.4f}, Z×{sz:.4f}")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    # Blender 4.0+ で export_selected は use_selection にリネームされた。
    # デフォルト False (全部エクスポート) で十分なので明示しない。
    bpy.ops.export_scene.gltf(
        filepath=os.path.abspath(output_path),
        export_format="GLB",
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
    )

    print(f"スケール補正完了 → {output_path}")


main()
