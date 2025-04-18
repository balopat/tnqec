import { Box, HStack, Icon, Text, IconButton } from '@chakra-ui/react'
import { FaExclamationCircle, FaTimes } from 'react-icons/fa'

interface ErrorPanelProps {
    error: string
    onDismiss: () => void
}

const ErrorPanel: React.FC<ErrorPanelProps> = ({ error, onDismiss }) => {
    return (
        <Box
            position="absolute"
            bottom={0}
            left={0}
            right={0}
            bg="red.100"
            borderTop="1px"
            borderColor="red.300"
            transform={error ? "translateY(0)" : "translateY(100%)"}
            transition="transform 0.15s ease-in-out"
            zIndex={1000}
        >
            <HStack spacing={3} p={4} justify="space-between">
                <HStack spacing={3}>
                    <Icon as={FaExclamationCircle} color="red.500" boxSize={5} />
                    <Text color="red.700">{error}</Text>
                </HStack>
                <IconButton
                    aria-label="Dismiss error"
                    icon={<Icon as={FaTimes} />}
                    size="sm"
                    variant="ghost"
                    colorScheme="red"
                    onClick={onDismiss}
                />
            </HStack>
        </Box>
    )
}

export default ErrorPanel 