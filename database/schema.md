# Prompt Pilot Database Schema

This document outlines the database schema for Prompt Pilot. We are using PostgreSQL.

## Tables

### 1. Users

*   **Purpose**: Stores information about users who can log in and use Prompt Pilot.
*   **Columns**:
    *   `user_id` SERIAL PRIMARY KEY: Unique identifier for the user.
    *   `username` VARCHAR(255) UNIQUE NOT NULL: User's chosen username.
    *   `email` VARCHAR(255) UNIQUE NOT NULL: User's email address.
    *   `password_hash` VARCHAR(255) NOT NULL: Hashed password for the user.
    *   `created_at` TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP: Timestamp of when the user account was created.
    *   `updated_at` TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP: Timestamp of when the user account was last updated.

### 2. AIModels

*   **Purpose**: Stores information about the different AI models available for use (e.g., GPT-3.5, Claude-2, Gemini Pro).
*   **Columns**:
    *   `model_id` SERIAL PRIMARY KEY: Unique identifier for the AI model.
    *   `model_name` VARCHAR(255) UNIQUE NOT NULL: Name of the AI model (e.g., "GPT-3.5 Turbo", "Claude Opus").
    *   `provider` VARCHAR(100): The company or organization providing the model (e.g., "OpenAI", "Anthropic", "Google").
    *   `description` TEXT: A brief description of the model.
    *   `config_schema` JSONB: A JSON schema defining the expected configuration parameters for this model (e.g., temperature, max_tokens).
    *   `created_at` TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP: Timestamp of when the model was added.

### 3. Prompts

*   **Purpose**: Stores the core prompt definitions. Each prompt can have multiple versions.
*   **Columns**:
    *   `prompt_id` SERIAL PRIMARY KEY: Unique identifier for a prompt.
    *   `user_id` INTEGER NOT NULL: Foreign key referencing `Users(user_id)`. The user who created this prompt.
    *   `name` VARCHAR(255) NOT NULL: A user-defined name for the prompt.
    *   `description` TEXT: A brief description of what the prompt is for.
    *   `created_at` TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP: Timestamp of when the prompt was created.
    *   `updated_at` TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP: Timestamp of when the prompt was last updated.
    *   FOREIGN KEY (`user_id`) REFERENCES `Users` (`user_id`) ON DELETE CASCADE
    *   UNIQUE (`user_id`, `name`)

### 4. PromptVersions

*   **Purpose**: Stores different versions of a specific prompt. This allows users to iterate and track changes.
*   **Columns**:
    *   `version_id` SERIAL PRIMARY KEY: Unique identifier for a prompt version.
    *   `prompt_id` INTEGER NOT NULL: Foreign key referencing `Prompts(prompt_id)`.
    *   `model_id` INTEGER NOT NULL: Foreign key referencing `AIModels(model_id)`. The AI model this version is intended for.
    *   `version_number` INTEGER NOT NULL: A sequential number indicating the version (e.g., 1, 2, 3).
    *   `prompt_text` TEXT NOT NULL: The actual text of the prompt for this version.
    *   `model_config` JSONB: Specific configuration parameters for the AI model for this version (e.g., temperature, max_tokens), conforming to `AIModels(config_schema)`.
    *   `created_at` TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP: Timestamp of when this version was created.
    *   `notes` TEXT: User notes about this specific version.
    *   FOREIGN KEY (`prompt_id`) REFERENCES `Prompts` (`prompt_id`) ON DELETE CASCADE
    *   FOREIGN KEY (`model_id`) REFERENCES `AIModels` (`model_id`)
    *   UNIQUE (`prompt_id`, `version_number`)

### 5. UserAIKeys

*   **Purpose**: Securely stores API keys for different AI models/providers linked to a user.
*   **Columns**:
    *   `key_id` SERIAL PRIMARY KEY: Unique identifier for the API key.
    *   `user_id` INTEGER NOT NULL: Foreign key referencing `Users(user_id)`.
    *   `model_provider` VARCHAR(100) NOT NULL: The provider of the AI model this key is for (e.g., "OpenAI", "Anthropic"). This helps in selecting the correct key.
    *   `api_key_encrypted` TEXT NOT NULL: The encrypted API key.
    *   `key_name` VARCHAR(255): A user-friendly name for the key (e.g., "My OpenAI Key").
    *   `created_at` TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP: Timestamp of when the key was added.
    *   `last_used_at` TIMESTAMP WITH TIME ZONE: Timestamp of when the key was last used.
    *   FOREIGN KEY (`user_id`) REFERENCES `Users` (`user_id`) ON DELETE CASCADE
    *   UNIQUE (`user_id`, `model_provider`, `key_name`)

### 6. APIEndpoints

*   **Purpose**: Stores information about API endpoints that users can create to expose their prompts.
*   **Columns**:
    *   `endpoint_id` SERIAL PRIMARY KEY: Unique identifier for the API endpoint.
    *   `user_id` INTEGER NOT NULL: Foreign key referencing `Users(user_id)`. The user who owns this endpoint.
    *   `endpoint_path` VARCHAR(255) UNIQUE NOT NULL: The unique path for the API endpoint (e.g., "/api/v1/summarize").
    *   `description` TEXT: A description of the endpoint.
    *   `is_active` BOOLEAN DEFAULT TRUE: Whether the endpoint is currently active and accessible.
    *   `created_at` TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP: Timestamp of when the endpoint was created.
    *   `updated_at` TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP: Timestamp of when the endpoint was last updated.
    *   FOREIGN KEY (`user_id`) REFERENCES `Users` (`user_id`) ON DELETE CASCADE

### 7. EndpointPromptMapping

*   **Purpose**: Links an API endpoint to a specific version of a prompt. This determines which prompt version is executed when an endpoint is called.
*   **Columns**:
    *   `mapping_id` SERIAL PRIMARY KEY: Unique identifier for the mapping.
    *   `endpoint_id` INTEGER NOT NULL: Foreign key referencing `APIEndpoints(endpoint_id)`.
    *   `version_id` INTEGER NOT NULL: Foreign key referencing `PromptVersions(version_id)`.
    *   `is_default` BOOLEAN DEFAULT TRUE: If multiple prompt versions are somehow linked (e.g. for A/B testing - future), this could mark the default. For now, assume one active version per endpoint.
    *   `created_at` TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP: Timestamp of when the mapping was created.
    *   FOREIGN KEY (`endpoint_id`) REFERENCES `APIEndpoints` (`endpoint_id`) ON DELETE CASCADE
    *   FOREIGN KEY (`version_id`) REFERENCES `PromptVersions` (`version_id`) ON DELETE CASCADE
    *   UNIQUE (`endpoint_id`, `version_id`) -- Ensures an endpoint doesn't map to the same version multiple times.
    *   UNIQUE (`endpoint_id`) WHERE `is_default` = TRUE -- Ensures only one default prompt version per endpoint.

### 8. HostedAPIs

*   **Purpose**: (Potentially for future use or specific scenarios) If Prompt Pilot itself hosts wrappers around external APIs that are then used by prompts. For now, this might be less critical if prompts directly call AI models.
*   **Columns**:
    *   `hosted_api_id` SERIAL PRIMARY KEY: Unique identifier for the hosted API.
    *   `name` VARCHAR(255) UNIQUE NOT NULL: Name of the hosted API.
    *   `base_url` VARCHAR(255) NOT NULL: Base URL for the API.
    *   `authentication_details` JSONB: How to authenticate with this API (e.g., API key, OAuth details).
    *   `created_at` TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP: Timestamp of creation.

### 9. APICallLogs

*   **Purpose**: Logs all incoming calls to the APIEndpoints created by users and outgoing calls to AI Models.
*   **Columns**:
    *   `log_id` SERIAL PRIMARY KEY: Unique identifier for the log entry.
    *   `timestamp` TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP: Time of the API call.
    *   `endpoint_id` INTEGER: Foreign key referencing `APIEndpoints(endpoint_id)` for incoming calls. NULL for direct AI model calls not via an endpoint.
    *   `prompt_id` INTEGER: Foreign key referencing `Prompts(prompt_id)`.
    *   `version_id` INTEGER: Foreign key referencing `PromptVersions(version_id)`.
    *   `user_id` INTEGER: Foreign key referencing `Users(user_id)`. The user who made the call or whose prompt was called.
    *   `request_payload` JSONB: The payload sent in the request.
    *   `response_payload` JSONB: The payload received in the response.
    *   `status_code` INTEGER: HTTP status code of the response (e.g., 200, 500).
    *   `duration_ms` INTEGER: Duration of the API call in milliseconds.
    *   `error_message` TEXT: Any error message if the call failed.
    *   `ip_address` VARCHAR(50): IP address of the caller (for incoming calls).
    *   `is_outgoing_call` BOOLEAN NOT NULL DEFAULT FALSE: True if this is a log for a call made *to* an AI model, False if it's an incoming call to a user's endpoint.
    *   `ai_model_id` INTEGER: Foreign key referencing `AIModels(model_id)` if it's an outgoing call to an AI model.
    *   FOREIGN KEY (`endpoint_id`) REFERENCES `APIEndpoints` (`endpoint_id`) ON DELETE SET NULL
    *   FOREIGN KEY (`prompt_id`) REFERENCES `Prompts` (`prompt_id`) ON DELETE SET NULL
    *   FOREIGN KEY (`version_id`) REFERENCES `PromptVersions` (`version_id`) ON DELETE SET NULL
    *   FOREIGN KEY (`user_id`) REFERENCES `Users` (`user_id`) ON DELETE SET NULL
    *   FOREIGN KEY (`ai_model_id`) REFERENCES `AIModels` (`model_id`) ON DELETE SET NULL

## Relationships Summary

*   A **User** can create multiple **Prompts**.
*   A **User** can have multiple **UserAIKeys** for different AI providers.
*   A **User** can define multiple **APIEndpoints**.
*   An **AIModel** is a general definition of a model that can be used.
*   A **Prompt** can have multiple **PromptVersions**.
*   Each **PromptVersion** is associated with one **Prompt** and one **AIModel**, and has specific `model_config`.
*   An **APIEndpoint** is mapped to a specific **PromptVersion** through **EndpointPromptMapping**. This determines what prompt is executed when the endpoint is called.
*   **APICallLogs** record requests and responses for both incoming calls to user-defined **APIEndpoints** and outgoing calls made by **PromptVersions** to **AIModels**.
*   **HostedAPIs** is a more specialized table, potentially for future use, if Prompt Pilot acts as a proxy or orchestration layer for other third-party APIs beyond just AI models.

This schema provides a comprehensive structure for managing users, prompts, AI models, API keys, and logging within Prompt Pilot.
The `JSONB` type is used for flexible fields like `config_schema` and `model_config` to store structured JSON data.
`ON DELETE CASCADE` is used where appropriate (e.g., if a User is deleted, their Prompts are also deleted). For logs, `ON DELETE SET NULL` is used to keep the log data even if the referenced entity is removed.
Timestamps are stored `WITH TIME ZONE` for better accuracy across different regions.
Unique constraints are added to prevent duplicate entries where logical (e.g., username, email, prompt name per user).
The `APICallLogs` table has an `is_outgoing_call` flag and an `ai_model_id` to differentiate between logs of incoming requests to user endpoints and outgoing requests to the actual AI models.
The `UserAIKeys` table includes `model_provider` to help quickly identify which key to use for a given `AIModel`.
The `EndpointPromptMapping` table has a unique constraint on `endpoint_id` where `is_default` is true, to ensure only one prompt version can be the default for an endpoint at any given time. This is a common pattern for implementing A/B testing or blue/green deployments at the endpoint level in the future, though for now, we assume one active version.
