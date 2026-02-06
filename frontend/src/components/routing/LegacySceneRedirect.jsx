import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

const LegacySceneRedirect = () => {
  const { scriptId } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    navigate(`/scenes/${scriptId}`, { replace: true });
  }, [scriptId, navigate]);

  return null;
};

export default LegacySceneRedirect;
