% 视频文件路径
videoFile = 'E:\第二个实验数据\front_data\wmv_data\231110_01_01_f.wmv';

% 提取文件名（不包含路径和扩展名）
[~, name, ~] = fileparts(videoFile);

% 构建输出文件路径，使文件名与输入文件相同
% 输出文件的扩展名改为 .csv
outputFile = fullfile('C:\Users\tangb\Desktop\机器学习', [name '.csv']);

% 创建视频读取器
v = VideoReader(videoFile);

% 设置追踪点的数量（用户可调整）
numPoints = 2; 

% 读取第一帧并选择特征点
frame = readFrame(v);
imshow(frame);
disp(['请选择 ' num2str(numPoints) ' 个特征点']);
[x, y] = getpts;

% 确保选择的点数量正确
if length(x) ~= numPoints
    error('选择的点数量与设定的追踪点数量不匹配，请重新运行并选择正确数量的点。');
end

points = [x y];
close;

% 创建点追踪器
pointTracker = vision.PointTracker('MaxBidirectionalError', 1);
initialize(pointTracker, points, frame);

% 创建视频播放器
videoPlayer = vision.VideoPlayer('Position', [100, 100, size(frame, 2), size(frame, 1)]);

% 用于存储追踪点的坐标
trackedPoints = zeros(0, 1 + 2 * numPoints); % 每帧 + 每个点的 (U, V)

% 追踪视频中的特征点
frameCount = 0;
while hasFrame(v)
    frameCount = frameCount + 1;
    frame = readFrame(v);
    [points, validity] = step(pointTracker, frame);
    
    % 仅保留有效的点
    validPoints = points(validity, :);
    
    % 如果有效点少于设定数量，跳过存储
    if size(validPoints, 1) < numPoints
        continue;
    end
    
    % 归一化坐标并反转 Y 坐标
    normalizedPoints = validPoints(1:numPoints, :) ./ [size(frame, 2), size(frame, 1)];
    normalizedPoints(:, 2) = 1 - normalizedPoints(:, 2); 
    
    % 存储数据
    trackedPoints(end+1, :) = [frameCount, normalizedPoints(:)']; 
    
    % 显示追踪点
    out = insertMarker(frame, validPoints(1:numPoints, :), '+', 'Color', 'red');
    step(videoPlayer, out);
end

% 创建带有表头的输出数据
headers = [{'Frame'}, arrayfun(@(i) {['U_' char('A' + i - 1)], ['V_' char('A' + i - 1)]}, 1:numPoints, 'UniformOutput', false)];
headers = [headers{:}];
outputData = [headers; num2cell(trackedPoints)];

% 输出到 CSV 文件
writecell(outputData, outputFile, 'Delimiter', ',');

% 释放资源
release(pointTracker);
release(videoPlayer);
