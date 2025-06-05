# 😼 Kitty Litter Box: Gmail Inbox Purr-fection Project Design 🗑️

**I. Overall Project Goal:**
To develop a personal tool that helps manage a cluttered Gmail inbox by providing actionable insights, automating common tasks (like deletion and organization), and eventually leveraging AI for deeper understanding and recommendations.

---

## II. Project Phases

### Phase One: Rule-Based Insights
* **Goal:** Retrieve email metadata to identify common patterns, high-volume senders, and large emails for basic analysis.
* **Key Insights (Examples):**
    * Top N Senders by Email Count (e.g., who sends the most emails).
    * Top N Senders by Total Email Size (cumulative size of emails from a sender, critical for storage).
    * Individual Emails with Large Attachments/Total Size (identify specific space hogs).
    * Age Distribution of Emails (e.g., count of emails older than 1 year, 2 years).
    * Total Unread Email Count.
* **Technical Steps:**
    1.  **Google Cloud Project Setup & Gmail API Enablement:** Create a project in Google Cloud, enable the Gmail API.
    2.  **Authentication:** Implement OAuth 2.0 using the Python Google Client Library. **Secrets (e.g., API key file path) will be managed via environment variables.**
    3.  **Retrieve Email Metadata:** Write Python code to fetch email metadata (sender, subject, date, size, attachment info) using `users.messages.list` and `users.messages.get` API calls, handling pagination for large inboxes.
    4.  **Data Processing:** Process retrieved JSON data into structured Python objects (e.g., list of dictionaries, potentially Pandas DataFrame).
    5.  **Generate Insights:** Develop functions to analyze this data and compute the defined insights.
    6.  **Present Insights:** Display results in a clear, readable format (e.g., print to console, simple text summary).
* **Open Questions/Considerations:**
    * What specific threshold defines a "large" email (e.g., >5MB, >10MB)?
    * Which specific metadata fields are essential for initial insights?

### Phase Two: Rule-Based Actions
* **Goal:** Expand the tool to take automated actions (delete, label, archive) based on insights from Phase One and user-defined rules.
* **Actions (Examples):**
    * **Delete:** Emails from specific senders, emails older than X days/months, emails larger than Y MB.
    * **Label/Move:** Emails from certain senders, emails with specific subject keywords, emails from newsletters.
* **Technical Steps (Future):**
    1.  **Extended Authentication:** Update Gmail API scope to allow write access (`gmail.modify` or `gmail.compose`).
    2.  **Action Functions:** Implement functions for deleting messages (`users.messages.delete`/`trash`) and applying/removing labels (`users.messages.modify`).
    3.  **Rule Engine:** Design a flexible way for users to define rules (e.g., simple configuration file, command-line parameters).
    4.  **Confirmation/Dry Run:** Implement a confirmation step before executing bulk actions to prevent accidental deletion.
* **Open Questions/Considerations:**
    * How will rules be defined by the user? (e.g., JSON config, simple CLI arguments).
    * Should rules be based on sender, subject, date, size, read status, etc.?

### Phase Three: AI-Powered Insights & Recommendations (Stretch Goal)
* **Goal:** Integrate Artificial Intelligence (specifically LLMs) to uncover deeper, semantic insights from email content and provide intelligent action recommendations, going beyond simple rule-based logic.
* **Insights/Recommendations (Examples):**
    * **Semantic Categorization:** (e.g., "This is a SaaS update," "This is a personalized offer," "This is a spam attempt").
    * **Sentiment Analysis:** (e.g., identifying urgent/negative emails).
    * **AI-Suggested Actions:** (e.g., "This looks like a promotional email - consider deleting," "This is an important update - consider starring").
* **Technical Steps (Future):**
    1.  **Content Extraction:** Securely extract full email body content (after initial metadata processing).
    2.  **Data Preparation for AI:** Clean and format text for LLM input.
    3.  **LLM API Integration:** Interact with a suitable LLM API (e.g., Google's Gemini API).
    4.  **Prompt Engineering:** Craft effective prompts to guide the AI to generate desired insights and recommendations.
    5.  **Parsing AI Output:** Process the LLM's natural language response into structured recommendations.
* **CRITICAL OPEN QUESTION: Privacy & Content Handling:**
    * **Core Challenge:** How to handle highly sensitive email content when sending it to an external AI service.
    * **Current Understanding/Approach:**
        * **Acceptance:** Acknowledge that the AI *will* process the content.
        * **Reliance on Provider:** Lean heavily on the AI provider's (e.g., Google) robust security, data handling policies, and commitment to not use data for model training.
        * **Purpose Limitation:** Explicitly state the data is *only* for insights/recommendations.
        * **Best Effort De-identification:** Consider client-side (your script) or provider-side (DLP services) attempts to redact specific PII *before* AI processing, understanding this is complex and might not be perfect.
        * **Transparency:** Crucially, your privacy policy *must* be explicit about content processing by AI.
    * **Why it's complex:** This involves philosophical, legal, and technical trade-offs. The goal is risk management and transparency, not zero risk.

---

## III. General Considerations:
* **Privacy:** Paramount throughout all phases. Emphasis on data minimization, transparency, consent, and secure processing.
* **Modularity:** Build the tool in distinct, reusable components (API interaction, data processing, insight generation, action execution) for easier development and future expansion.
* **User Interface:** Initially command-line based. Could evolve to a simple web interface later if desired.
