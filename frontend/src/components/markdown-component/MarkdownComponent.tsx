import React from 'react';
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useLiveAPIContext } from '../../contexts/LiveAPIContext';
import {Prism as SyntaxHighlighter} from 'react-syntax-highlighter'
import './MarkdownComponent.scss';


const LessonContentDisplay = ({  }) => {
    const { toolImage, currentSectionMarkdown } = useLiveAPIContext();

  if (!currentSectionMarkdown || toolImage) {
    return null;
  }

  return (
  <div className="lesson-content-display">
    <Markdown
      remarkPlugins={[remarkGfm]}
      components={{
        code(props: any) {
          const {children, className, node, ...rest} = props
          const match = /language-(\w+)/.exec(className || '')
          return match ? (
            <SyntaxHighlighter
              {...rest}
              PreTag="div"
              children={String(children).replace(/\n$/, '')}
              language={match[1]}
              // You may need to import or define a style, e.g. `style={dark}`
            />
          ) : (
            <code {...rest} className={className}>
              {children}
            </code>
          )
        }
      }}
    >
      {currentSectionMarkdown}
    </Markdown>
  </div>
  );
};

export default LessonContentDisplay;