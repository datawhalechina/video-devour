import ParagraphBlock from './Blocks/ParagraphBlock'
import HeadingBlock from './Blocks/HeadingBlock'
import ListBlock, { ListItemBlock, TodoListItemBlock } from './Blocks/ListBlock'
import QuoteBlock from './Blocks/QuoteBlock'
import CalloutBlock from './Blocks/CalloutBlock'
import ImageBlock from './Blocks/ImageBlock'
import VideoBlock from './Blocks/VideoBlock'
import DividerBlock from './Blocks/DividerBlock'
import { BLOCK_TYPES } from './editorConfig'

/**
 * 渲染编辑器元素（块级）
 */
function EditorElement({ attributes, children, element }) {
  switch (element.type) {
    case BLOCK_TYPES.PARAGRAPH:
      return <ParagraphBlock attributes={attributes} element={element}>{children}</ParagraphBlock>
    
    case BLOCK_TYPES.HEADING_1:
    case BLOCK_TYPES.HEADING_2:
    case BLOCK_TYPES.HEADING_3:
      return <HeadingBlock attributes={attributes} element={element}>{children}</HeadingBlock>
    
    case BLOCK_TYPES.BULLET_LIST:
    case BLOCK_TYPES.NUMBERED_LIST:
      return <ListBlock attributes={attributes} element={element}>{children}</ListBlock>
    
    case 'list-item':
      return <ListItemBlock attributes={attributes} element={element}>{children}</ListItemBlock>
    
    case BLOCK_TYPES.TODO_LIST:
      return <TodoListItemBlock attributes={attributes} element={element}>{children}</TodoListItemBlock>
    
    case BLOCK_TYPES.QUOTE:
      return <QuoteBlock attributes={attributes} element={element}>{children}</QuoteBlock>
    
    case BLOCK_TYPES.CALLOUT:
      return <CalloutBlock attributes={attributes} element={element}>{children}</CalloutBlock>
    
    case BLOCK_TYPES.IMAGE:
      return <ImageBlock attributes={attributes} element={element}>{children}</ImageBlock>
    
    case BLOCK_TYPES.VIDEO:
      return <VideoBlock attributes={attributes} element={element}>{children}</VideoBlock>
    
    case BLOCK_TYPES.DIVIDER:
      return <DividerBlock attributes={attributes} element={element}>{children}</DividerBlock>
    
    case 'link':
      return (
        <a
          {...attributes}
          href={element.url}
          className="text-primary-600 underline hover:text-primary-700 cursor-pointer"
          target="_blank"
          rel="noopener noreferrer"
        >
          {children}
        </a>
      )
    
    default:
      return <ParagraphBlock attributes={attributes} element={element}>{children}</ParagraphBlock>
  }
}

export default EditorElement

