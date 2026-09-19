# VideoDevour logo

当前使用用户提供原图的清理版本：保留鲸鱼与胶片的造型，清理底部水印、外围水滴与爱心、白色背景。没有采用此前重新设计的扁平或立体鲸鱼。

使用内置 image_gen 编辑原图、修补水印覆盖部分；背景先清为纯白，再沿用项目图标导出脚本转透明。原图编辑是生成式修补，并非逐像素无损处理。清理后的白底源图为 `icon-source.png`，透明主图为 `icon-1024.png`。

运行 `python3 desktop/make_icons.py` 重新导出网页 Logo、16/32 像素 favicon、Apple Touch 图标和桌面 ICO/ICNS。`favicon.svg` 内嵌 PNG，不是矢量路径文件。前端资源使用版本参数刷新缓存；桌面安装包需要重新构建才能采用新图标。

## Cleanup prompt

Use case: precise-object-edit / background-extraction. This is a STRICT CLEANUP of the user's original image, NOT logo generation or redesign. Keep the ORIGINAL whale and ORIGINAL film frame exactly as supplied: same silhouette, pose, proportions, big round head, two closed eyes, pink cheeks, teeth, hand, curved tail, blue colors, dark blue drawn outlines, hand-painted soft shading, white belly, gray film frame with its original sprocket holes, and original gray play triangle. Do NOT beautify, reinterpret, stylize, change linework, change expression, or convert to 3D or flat vector. The user explicitly rejected redesigns and wants THIS exact original artwork. Remove only: (1) the gray watermark text and small watermark symbol over the bottom whale body/tail, seamlessly repairing ONLY the pixels underneath to continue existing belly/tail shading and outlines; (2) all detached background decorations including the top right blue heart and all separate blue water droplets; (3) the background. Deliver just the unchanged original whale holding the unchanged film frame, as a clean isolated cutout. Prefer genuine alpha transparency if supported; NEVER draw checkerboard transparency. If true alpha cannot be emitted, use a perfectly uniform opaque PURE WHITE #FFFFFF background, with no gray texture, no shadows outside artwork and absolutely NO checkerboard. Preserve the full tail and frame without clipping. Center the original artwork with a small even margin. No text, no new elements. Exact original design preservation is more important than any polish.

## Final background correction prompt

Change ONLY the checkered background to uniform opaque PURE WHITE #FFFFFF. This includes every gray checkerboard square outside the whale and the gray checkerboard inside the four small holes in the LEFT side of the movie frame. Preserve absolutely everything else, exactly: whale silhouette, proportions, eyes, mouth, colors, outlines, shading, tail, flipper, gray movie frame, white screen and gray play triangle. Do not redraw or restyle any subject. Keep current image dimensions and composition unchanged. WHITE OPAQUE background, NO transparency, NO checkerboard, no gray squares, no texture, no outside shadows. Output only the cleaned original art on a completely uniform white background.
