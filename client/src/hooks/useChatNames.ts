import { useState, useEffect } from "react";
import { getSingleton, queryFirstResource } from "../api/client";

/**
 * Load the bot display name (from Chatbot.botname) and user display name
 * (from User.username) and expose them reactively.
 *
 * Returns fallbacks ("Computer" / "You") while loading or on error so the
 * chat UI never shows blank labels.
 */
export function useChatNames() {
  const [botName, setBotName] = useState("Computer");
  const [userName, setUserName] = useState("You");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [user, chatbot] = await Promise.all([
          getSingleton("User").catch(() => null),
          queryFirstResource("Chatbot", {
            current: true,
          } as Record<string, unknown>).catch(() => null),
        ]);

        if (cancelled) return;

        if (user?.username) {
          setUserName(String(user.username));
        }
        if (chatbot?.record?.botname) {
          setBotName(String(chatbot.record.botname));
        }
      } catch {
        // keep defaults
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { botName, userName };
}
