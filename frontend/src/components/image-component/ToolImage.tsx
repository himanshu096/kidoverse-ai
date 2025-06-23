// src/components/ToolImageOverlay.tsx
import { useEffect } from 'react'; 
import { useLiveAPIContext } from "../../contexts/LiveAPIContext";
import "./ToolImage.scss";

export default function ToolImage() {
  const { toolImage, setToolImage } = useLiveAPIContext();

   // Use useEffect to manage the timer for clearing the image
  useEffect(() => {
    let timer: NodeJS.Timeout | undefined; 

    if (toolImage) {
      timer = setTimeout(() => {
        setToolImage(null);
      }, 20000);
    }
    // Cleanup function: This runs when the component unmounts,
    // or when 'toolImage' or 'setToolImage' in the dependency array changes
    return () => {
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [toolImage, setToolImage]); // 
  

  if (!toolImage) return null;

  return (
    <div className="tool-image-container">
      <img
        src={toolImage.url}
        alt={toolImage.alt || "Visual aid"}
        className="tool-image-placeholder"
      />
    </div>
  );
}
