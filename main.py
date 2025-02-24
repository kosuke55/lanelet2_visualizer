from flask import Flask, render_template, jsonify, request
import os
import lanelet2
import json
import traceback
import lanelet2.core
import lanelet2.geometry
import lanelet2.projection
import lanelet2.io
import lanelet2.routing
import lanelet2.traffic_rules
from autoware_lanelet2_extension_python.projection import MGRSProjector

app = Flask(__name__)

def load_osm_file(file_path):
    try:
        print(f"Loading file: {file_path}")
        
        # ファイルの存在確認
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # ファイルのパーミッション確認
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"Permission denied: {file_path}")
        
        try:
            # プロジェクタの設定（東京付近の座標を使用）
            origin = lanelet2.io.Origin(35.681236, 139.767125)  # 東京駅付近
            projector = lanelet2.projection.UtmProjector(origin)
            
            # マップの読み込み
            lanelet_map = lanelet2.io.load(file_path, projector)
            print(f"Map loaded successfully")
            
            map_data = {
                'lanelets': [],
                'bounds': {
                    'min_x': float('inf'),
                    'min_y': float('inf'),
                    'max_x': float('-inf'),
                    'max_y': float('-inf')
                }
            }
            
            if not lanelet_map:
                print(f"Warning: No map data found in {file_path}")
                return map_data
            
            # laneletLayerの取得
            lanelet_layer = lanelet_map.laneletLayer
            if not lanelet_layer:
                print(f"Warning: No lanelet layer found in {file_path}")
                return map_data
            
            print(f"Number of lanelets: {len(lanelet_layer)}")
            
            # レーンの中心線と境界線を取得
            for lanelet in lanelet_layer:
                try:
                    left_points = []
                    right_points = []
                    center_points = []
                    
                    try:
                        # 左境界線
                        left_bound = lanelet.leftBound
                        if left_bound is not None:
                            for point in left_bound:
                                try:
                                    x = float(point.x)
                                    y = float(point.y)
                                    left_points.append([x, y])
                                    map_data['bounds']['min_x'] = min(map_data['bounds']['min_x'], x)
                                    map_data['bounds']['min_y'] = min(map_data['bounds']['min_y'], y)
                                    map_data['bounds']['max_x'] = max(map_data['bounds']['max_x'], x)
                                    map_data['bounds']['max_y'] = max(map_data['bounds']['max_y'], y)
                                except (AttributeError, ValueError) as e:
                                    print(f"Error processing point in left bound: {str(e)}")
                                    continue
                    except Exception as e:
                        print(f"Error processing left bound of lanelet {lanelet.id}: {str(e)}")
                    
                    try:
                        # 右境界線
                        right_bound = lanelet.rightBound
                        if right_bound is not None:
                            for point in right_bound:
                                try:
                                    x = float(point.x)
                                    y = float(point.y)
                                    right_points.append([x, y])
                                    map_data['bounds']['min_x'] = min(map_data['bounds']['min_x'], x)
                                    map_data['bounds']['min_y'] = min(map_data['bounds']['min_y'], y)
                                    map_data['bounds']['max_x'] = max(map_data['bounds']['max_x'], x)
                                    map_data['bounds']['max_y'] = max(map_data['bounds']['max_y'], y)
                                except (AttributeError, ValueError) as e:
                                    print(f"Error processing point in right bound: {str(e)}")
                                    continue
                    except Exception as e:
                        print(f"Error processing right bound of lanelet {lanelet.id}: {str(e)}")
                    
                    # 中心線の取得
                    try:
                        center_line = lanelet.centerline
                        if center_line is not None:
                            for point in center_line:
                                try:
                                    x = float(point.x)
                                    y = float(point.y)
                                    center_points.append([x, y])
                                except (AttributeError, ValueError) as e:
                                    print(f"Error processing point in center line: {str(e)}")
                                    continue
                    except Exception as e:
                        print(f"Error processing center line of lanelet {lanelet.id}: {str(e)}")
                    
                    if left_points or right_points:  # 少なくとも片方の境界線がある場合のみ追加
                        try:
                            lanelet_id = str(lanelet.id)
                            print(f"Lanelet {lanelet_id} processed: {len(left_points)} left points, {len(right_points)} right points, {len(center_points)} center points")
                            
                            map_data['lanelets'].append({
                                'id': lanelet_id,
                                'left': left_points,
                                'right': right_points,
                                'center': center_points
                            })
                        except Exception as e:
                            print(f"Error adding lanelet to map_data: {str(e)}")
                            continue
                except Exception as e:
                    print(f"Error processing lanelet: {str(e)}")
                    continue
            
            print(f"Total lanelets processed: {len(map_data['lanelets'])}")
            if map_data['lanelets']:
                print(f"Map bounds: {map_data['bounds']}")
            return map_data
            
        except Exception as e:
            print(f"Error processing map {file_path}: {str(e)}")
            print(traceback.format_exc())
            raise
            
    except Exception as e:
        print(f"Error loading {file_path}: {str(e)}")
        print(traceback.format_exc())
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/list_contents', methods=['POST'])
def list_contents():
    directory = request.json.get('directory', '.')
    try:
        # 絶対パスを取得
        abs_path = os.path.abspath(directory)
        
        # ディレクトリとファイルの一覧を取得
        contents = {
            'current_dir': abs_path,
            'parent_dir': os.path.dirname(abs_path),
            'directories': [],
            'osm_files': []
        }
        
        for item in os.listdir(directory):
            full_path = os.path.join(directory, item)
            if os.path.isdir(full_path):
                contents['directories'].append({
                    'name': item,
                    'path': full_path
                })
            elif item.endswith('.osm'):
                contents['osm_files'].append({
                    'name': item,
                    'path': full_path
                })
        
        return jsonify(contents)
    except Exception as e:
        print(f"Error listing contents: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 400

@app.route('/list_maps', methods=['POST'])
def list_maps():
    directory = request.json.get('directory', '.')
    osm_files = []
    
    try:
        # ディレクトリの存在確認
        if not os.path.exists(directory):
            return jsonify({'error': f"Directory not found: {directory}"}), 404
        
        if not os.path.isdir(directory):
            return jsonify({'error': f"Not a directory: {directory}"}), 400
        
        print(f"Scanning directory: {directory}")
        for file in os.listdir(directory):
            if file.endswith('.osm'):
                full_path = os.path.join(directory, file)
                try:
                    print(f"Processing file: {full_path}")
                    map_data = load_osm_file(full_path)
                    if map_data['lanelets']:  # レーンレットが存在する場合のみ追加
                        osm_files.append({
                            'name': file,
                            'path': full_path,
                            'data': map_data
                        })
                        print(f"Successfully processed {file}")
                    else:
                        print(f"No lanelets found in {file}")
                except Exception as e:
                    print(f"Error processing {full_path}: {str(e)}")
                    print(traceback.format_exc())
                    # 個別のファイルのエラーはスキップして続行
                    continue
        
        print(f"Total OSM files processed: {len(osm_files)}")
        return jsonify(osm_files)
    except Exception as e:
        print(f"Error in list_maps: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5001) 