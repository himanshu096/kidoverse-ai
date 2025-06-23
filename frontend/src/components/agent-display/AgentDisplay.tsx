import { useLiveAPIContext } from '../../contexts/LiveAPIContext';
import { useAgentState } from '../../hooks/use-agent-state';
import ToolImage from '../image-component/ToolImage';
import MarkdownComponent from '../markdown-component/MarkdownComponent';

export default function AgentDisplay() {
  const { toolImage, currentSectionMarkdown, connected, inVolume, volume, feedbackMessage } = useLiveAPIContext();
  const agentStateImage = useAgentState({ connected, inVolume, volume });

  const isContentActive = !!toolImage || !!currentSectionMarkdown;

  return (
    <div className="main-app-content">
      {feedbackMessage && (
        <div className="feedback-message">
          <p>{feedbackMessage.message}</p>
        </div>
      )}
      {!isContentActive && (
        <img
          src={agentStateImage}
          alt="AI Animation"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover'
          }}
        />
      )}
      <ToolImage />
      <MarkdownComponent />
    </div>
  );
} 