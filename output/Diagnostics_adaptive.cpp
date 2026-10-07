/**
 * @file VsmVehicleSpeedMonitor.cpp
 * @brief Implementation of the Vehicle Speed Monitor Software Component (SWC).
 * 
 * This module implements the logic to monitor vehicle speed via a signal input
 * and trigger a diagnostic event if the speed exceeds a defined threshold (100 km/h).
 * It adheres to AUTOSAR Adaptive Platform conventions using the `ara::com` and 
 * `ara::diag` namespaces.
 */

#include <memory>
#include "VsmVehicleSpeedMonitor.h"
#include "VsmInternalTypes.h" // Assumed internal header defining SpeedType, etc.

namespace ara {
    namespace com {
        /**
         * @class VehicleSpeedMonitor
         * @brief SWC responsible for monitoring vehicle speed and reporting over-speed conditions.
         */
        class VehicleSpeedMonitor : public ISpeedMonitor {
        public:
            /**
             * @brief Constructs the Vehicle Speed Monitor instance.
             * Initializes internal state machines and registers necessary interfaces.
             */
            VehicleSpeedMonitor() = default;

            ~VehicleSpeedMonitor() override = default;

            /**
             * @brief Sets the current vehicle speed value.
             * 
             * @param[in] speed The current speed in km/h.
             * @return true if the update was successful, false otherwise.
             */
            bool setSpeed(SpeedType speed) override {
                // Validate input range based on type definition constraints
                if (speed > static_cast<SpeedType>(MAX_ALLOWED_SPEED)) {
                    return false;
                }

                m_currentSpeed.store(speed);
                
                // Check against threshold immediately upon update
                checkThreshold();
                
                return true;
            }

            /**
             * @brief Gets the currently monitored speed.
             * 
             * @return const SpeedType& Reference to the current speed.
             */
            const SpeedType& getSpeed() const override {
                return m_currentSpeed.load();
            }

            /**
             * @brief Checks if the current speed exceeds the configured limit.
             * Triggers a diagnostic event if applicable.
             */
            void checkThreshold() {
                const SpeedType THRESHOLD_KMH = 100u; // Requirement: Exceeds 100 km/h
                
                auto currentSpeed = m_currentSpeed.load();

                if (currentSpeed > THRESHOLD_KMH) {
                    // Trigger Over-Speed Diagnostic Event
                    // Assuming a standard DId or Event ID exists for this condition.
                    // In a real implementation, this would map to a specific 
                    // DiagnosticEventID defined in the configuration.
                    
                    // Example: Triggering a generic 'OverSpeed' event
                    // Note: Specific Event IDs should be taken from the generated 
                    // DiagnosticEvents table or configuration file.
                    diag::triggerDiagnosticEvent(
                        diag::EventType::OVER_SPEED_WARNING, 
                        diag::Severity::WARNING,
                        diag::TriggerReason::SPEED_EXCEEDED_LIMIT
                    );
                } else {
                    // Optionally clear warning status if it was previously active
                    // This depends on whether the requirement implies latching behavior.
                    // Assuming non-latching for immediate reaction unless specified.
                    // If latching is required, logic here would differ.
                }
            }

        private:
            // Thread-safe storage for speed updates
            std::atomic<SpeedType> m_currentSpeed{0};
            
            // Configuration constant derived from requirement
            constexpr static uint32_t MAX_ALLOWED_SPEED = 400u; // Arbitrary max for type safety
            
            // Helper to access diag namespace directly within member functions
            // In strict implementations, this might be passed as a dependency or accessed via global config.
            static inline diag::DiagnosticManager& getDiagMgr() {
                static diag::DiagnosticManager mgr;
                return mgr;
            }
        };

        /**
         * @brief Factory function to create a new instance of VehicleSpeedMonitor.
         * 
         * @return std::unique_ptr<VehicleSpeedMonitor> Pointer to the created instance.
         */
        std::unique_ptr<VehicleSpeedMonitor> createInstance() {
            return std::make_unique<VehicleSpeedMonitor>();
        }

    } // namespace com
} // namespace ara
